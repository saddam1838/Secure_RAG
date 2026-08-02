import os
import json
import uuid
from typing import List, Dict, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, PayloadSchemaType,
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
            for field_name in ["document_id", "uploaded_by"]:
                try:
                    self.qdrant.create_payload_index(
                        collection_name=settings.QDRANT_COLLECTION,
                        field_name=field_name,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass
            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            print("✅ Connected to Supabase")
        except Exception as e:
            print(f"⚠️ Cloud connection failed: {e}")
            self.qdrant = None
            self.supabase = None

    @property
    def is_cloud_enabled(self) -> bool:
        return self.qdrant is not None and self.supabase is not None

    def register_user(self, username: str, password_hash: str, role: str = "user") -> Tuple[bool, str]:
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
        result = self.supabase.table("users").select("*").eq("username", username).execute()
        return result.data[0] if result.data else None

    def save_document(self, filename: str, content_hash: str, content: str, size_mb: float,
                     uploaded_by: str, is_safe: bool, scan_issues: List[Dict], ) -> Tuple[bool, str]:
        if not self.is_cloud_enabled:
            return False, "Cloud storage not available"
        try:
            # 🔥 CRITICAL FIX: Make the hash user-specific to bypass global unique constraints
            user_specific_hash = f"{uploaded_by}_{content_hash}"
            
            self.supabase.table("documents").insert({
                "filename": filename,
                "file_hash": user_specific_hash,
                "content": content,
                "size_mb": size_mb,
                "uploaded_by": uploaded_by,
                "is_safe": is_safe,
                "scan_issues": json.dumps(scan_issues) if scan_issues else None,
                
            }).execute()
            return True, "Document saved"
        except Exception as e:
            print(f"❌ Failed to save document: {e}")
            return False, str(e)

    def document_exists_for_user(self, content_hash: str, username: str) -> bool:
        if not self.is_cloud_enabled:
            return False
        try:
            user_specific_hash = f"{username}_{content_hash}"
            result = (
                self.supabase.table("documents")
                .select("id")
                .eq("file_hash", user_specific_hash)
                .execute()
            )
            exists = len(result.data) > 0
            if exists:
                print(f"⚠️ Document with hash '{user_specific_hash}' still exists in Supabase for '{username}'")
            return exists
        except Exception as e:
            print(f"❌ Error checking document existence: {e}")
            return False

    def get_all_safe_documents(self) -> List[Dict]:
        if not self.is_cloud_enabled:
            return []
        result = self.supabase.table("documents").select("*").eq("is_safe", True).execute()
        return result.data

    def delete_document(self, document_id: str, username: str) -> Tuple[bool, str]:
        if not self.is_cloud_enabled:
            return False, "Cloud storage not available"
        try:
            check = (
                self.supabase.table("documents")
                .select("id")
                .eq("id", document_id)
                .eq("uploaded_by", username)
                .execute()
            )
            if not check.data:
                return False, "Document not found or you do not have permission."

            self.supabase.table("documents").delete().eq("id", document_id).execute()
            self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
            )
            self.log_audit(username, "document_deleted", {"document_id": document_id})
            return True, "Document deleted successfully."
        except Exception as e:
            return False, f"Deletion failed: {str(e)}"

    def store_vectors(self, embeddings: List[List[float]], metadatas: List[Dict],
                     document_id: str, uploaded_by: str) -> bool:
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
                        payload={**meta, "document_id": document_id, "uploaded_by": uploaded_by},
                    )
                )
            self.qdrant.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
            return True
        except Exception as e:
            print(f"⚠️ Vector storage failed: {e}")
            return False

    def search_vectors(self, query_embedding: List[float], k: int = 10,
                      uploaded_by: Optional[str] = None) -> List[Dict]:
        if not self.is_cloud_enabled:
            return []
        search_filter = None
        if uploaded_by:
            search_filter = Filter(
                must=[FieldCondition(key="uploaded_by", match=MatchValue(value=uploaded_by))]
            )
        try:
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
                    "chunk_id": r.payload.get("chunk_id", str(r.id)),
                    "uploaded_by": r.payload.get("uploaded_by", "unknown"),
                    "score": r.score,
                }
                for r in results.points
            ]
        except Exception as e:
            print(f"❌ Qdrant search failed: {e}")
            return []

    def log_audit(self, username: str, action: str, details: Dict) -> bool:
        if not self.is_cloud_enabled:
            return False
        try:
            self.supabase.table("audit_logs").insert(
                {"username": username, "action": action, "details": details}
            ).execute()
            return True
        except Exception as e:
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
