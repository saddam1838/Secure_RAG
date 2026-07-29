"""
Cloud Storage Service - Enterprise-grade persistence using Qdrant + Supabase.
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from supabase import create_client, Client
from config import settings


class CloudStorageService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.qdrant: Optional[QdrantClient] = None
        self.supabase: Optional[Client] = None
        self._connect()

    def _connect(self):
        if not settings.USE_CLOUD_STORAGE:
            print("️ Cloud storage disabled. Using local fallback.")
            return

        try:
            self.qdrant = QdrantClient(
                url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=30
            )
            collections = [c.name for c in self.qdrant.get_collections().collections]

            if settings.QDRANT_COLLECTION not in collections:
                self.qdrant.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                print(f"✅ Created Qdrant collection: {settings.QDRANT_COLLECTION}")
            else:
                print(
                    f"✅ Connected to Qdrant collection: {settings.QDRANT_COLLECTION}"
                )

            # FIX: Create a payload index for 'document_id' so we can filter/delete by it
            try:
                self.qdrant.create_payload_index(
                    collection_name=settings.QDRANT_COLLECTION,
                    field_name="document_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                print("✅ Created Qdrant payload index for 'document_id'")
            except Exception:
                pass  # Index already exists, which is fine

            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            print("✅ Connected to Supabase")
        except Exception as e:
            print(f"⚠️ Cloud connection failed: {e}. Falling back to local storage.")
            self.qdrant = None
            self.supabase = None

    @property
    def is_cloud_enabled(self) -> bool:
        return self.qdrant is not None and self.supabase is not None

    def register_user(
        self, username: str, password_hash: str, role: str = "user"
    ) -> Tuple[bool, str]:
        if not self.is_cloud_enabled:
            return False, "Cloud storage not available"
        try:
            self.supabase.table("users").insert(
                {"username": username, "password_hash": password_hash, "role": role}
            ).execute()
            return True, "User registered"
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return False, "Username already exists"
            return False, str(e)

    def get_user(self, username: str) -> Optional[Dict]:
        if not self.is_cloud_enabled:
            return None
        result = (
            self.supabase.table("users").select("*").eq("username", username).execute()
        )
        return result.data[0] if result.data else None

    def save_document(
        self,
        filename: str,
        file_hash: str,
        content: str,
        size_mb: float,
        uploaded_by: str,
        is_safe: bool,
        scan_issues: List[Dict],
    ) -> Tuple[bool, str]:
        if not self.is_cloud_enabled:
            return False, "Cloud storage not available"
        try:
            self.supabase.table("documents").insert(
                {
                    "filename": filename,
                    "file_hash": file_hash,
                    "content": content,
                    "size_mb": size_mb,
                    "uploaded_by": uploaded_by,
                    "is_safe": is_safe,
                    "scan_issues": json.dumps(scan_issues) if scan_issues else None,
                }
            ).execute()
            return True, "Document saved"
        except Exception as e:
            return False, str(e)

    def document_exists(self, file_hash: str) -> bool:
        if not self.is_cloud_enabled:
            return False
        result = (
            self.supabase.table("documents")
            .select("id")
            .eq("file_hash", file_hash)
            .execute()
        )
        return len(result.data) > 0

    def get_all_safe_documents(self) -> List[Dict]:
        if not self.is_cloud_enabled:
            return []
        result = (
            self.supabase.table("documents").select("*").eq("is_safe", True).execute()
        )
        return result.data

    def delete_document(self, document_id: str, username: str) -> Tuple[bool, str]:
        """Securely delete a document. Enforces ownership check."""
        if not self.is_cloud_enabled:
            return False, "Cloud storage not available"
        try:
            # 1. SECURITY CHECK: Verify the document belongs to this user
            check = (
                self.supabase.table("documents")
                .select("id")
                .eq("id", document_id)
                .eq("uploaded_by", username)
                .execute()
            )
            if not check.data:
                return (
                    False,
                    "Document not found or you do not have permission to delete it.",
                )

            # 2. Delete metadata and content from Supabase
            self.supabase.table("documents").delete().eq("id", document_id).execute()

            # 3. Delete vectors from Qdrant using the indexed payload field
            self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        )
                    ]
                ),
            )

            # 4. Log the deletion
            self.log_audit(username, "document_deleted", {"document_id": document_id})
            return True, "Document deleted successfully."
        except Exception as e:
            return False, f"Deletion failed: {str(e)}"

    def store_vectors(
        self, embeddings: List[List[float]], metadatas: List[Dict], document_id: str
    ) -> bool:
        if not self.is_cloud_enabled:
            return False
        try:
            points = []
            for i, (emb, meta) in enumerate(zip(embeddings, metadatas)):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}-{i}"))
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=emb,
                        payload={**meta, "document_id": document_id},
                    )
                )
            self.qdrant.upsert(
                collection_name=settings.QDRANT_COLLECTION, points=points
            )
            return True
        except Exception as e:
            print(f"⚠️ Vector storage failed: {e}")
            return False

    def search_vectors(
        self,
        query_embedding: List[float],
        k: int = 10,
        user_filter: Optional[str] = None,
    ) -> List[Dict]:
        if not self.is_cloud_enabled:
            return []

        search_filter = None
        if user_filter:
            search_filter = Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=user_filter))]
            )

        results = self.qdrant.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_embedding,
            limit=k,
            query_filter=search_filter,
            with_payload=True,
        )

        return [
            {
                "text": r.payload.get("text", ""),
                "source": r.payload.get("source", "unknown"),
                "category": r.payload.get("category", "general"),
                "chunk_id": r.payload.get("chunk_id", str(r.id)),
                "score": r.score,
            }
            for r in results.points
        ]

    def log_audit(self, username: str, action: str, details: Dict) -> bool:
        if not self.is_cloud_enabled:
            return False
        try:
            self.supabase.table("audit_logs").insert(
                {"username": username, "action": action, "details": details}
            ).execute()
            return True
        except Exception as e:
            print(f"⚠️ Audit log failed: {e}")
            return False

    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        if not self.is_cloud_enabled:
            return []
        result = (
            self.supabase.table("audit_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data


cloud_storage = CloudStorageService()
