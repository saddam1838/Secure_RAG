import hashlib
import uuid
import os
import numpy as np
from typing import List, Dict, Optional
from services.cloud_storage import cloud_storage
from config import settings
from models.vector_store import FAISSStore

class RAGService:
    def __init__(self):
        self.use_cloud = cloud_storage.is_cloud_enabled
        # 🔥 MULTI-USER LOCAL STORAGE: Each user gets their own isolated FAISS & memory
        self.user_corpuses = {}      # {username: [chunk_text, ...]}
        self.user_metadatas = {}     # {username: [{chunk_id, source, ...}, ...]}
        self.user_faiss = {}         # {username: FAISSStore}
        self.current_user = None     # Context for current request
        
    def _get_user_faiss(self, username: str) -> FAISSStore:
        """Initialize or retrieve the local FAISS index for a specific user."""
        if username not in self.user_faiss:
            self.user_faiss[username] = FAISSStore(dim=384)
            self.user_corpuses[username] = []
            self.user_metadatas[username] = []
        return self.user_faiss[username]

    def load_user_data(self, username: str):
        """Load all chunks for this user from Qdrant into local FAISS + memory."""
        if not username:
            return  # Prevent Qdrant MatchValue(None) error during cache warmup
        if not username:
            return  # Prevent Qdrant MatchValue(None) error during cache warmup
            
        if username in self.user_corpuses and len(self.user_corpuses[username]) > 0:
            return  # Already loaded in memory
            
        faiss_store = self._get_user_faiss(username)
        
        if self.use_cloud:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                print(f"🔄 Syncing cloud data to local FAISS for '{username}'...")
                scroll_result = cloud_storage.qdrant.scroll(
                    collection_name=settings.QDRANT_COLLECTION,
                    scroll_filter=Filter(must=[FieldCondition(key="uploaded_by", match=MatchValue(value=username))]),
                    limit=10000,
                    with_payload=True,
                    with_vectors=True  # 🔥 Need vectors to build local FAISS!
                )
                points = scroll_result[0]
                if points:
                    texts = []
                    vectors = []
                    metas = []
                    for p in points:
                        payload = p.payload
                        text = payload.get("text", "")
                        if text and p.vector is not None:
                            texts.append(text)
                            vectors.append(p.vector)
                            metas.append({
                                "chunk_id": payload.get("chunk_id", str(p.id)),
                                "source": payload.get("source", "unknown"),
                                "uploaded_by": username,
                                "text": text
                            })
                    if vectors:
                        vectors_np = np.array(vectors).astype('float32')
                        faiss_store.add(vectors_np, metas)
                        self.user_corpuses[username] = texts
                        self.user_metadatas[username] = metas
                        print(f"✅ Loaded {len(texts)} chunks for '{username}' into local FAISS.")
                else:
                    print(f"ℹ️ No documents found for user '{username}' in cloud.")
            except Exception as e:
                print(f"⚠️ Failed to load user data from cloud: {e}")

    def _chunk_document(self, content: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            from models.model_manager import ModelManager
            mm = ModelManager()
            embedder = mm.get_embedder()
            return embedder.encode(texts).tolist()
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return [[0.0] * 384 for _ in texts]

    def add_document(self, content: str, metadata: Dict = None, uploaded_by: str = "admin"):
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check cloud dedup
        if self.use_cloud and cloud_storage.document_exists_for_user(content_hash, uploaded_by):
            print(f"ℹ️ Document already exists for user '{uploaded_by}'")
            return

        chunks = self._chunk_document(content)
        if not chunks:
            return

        # Dedup chunks for this specific user
        unique_chunks = []
        user_chunk_hashes = {m.get("chunk_id") for m in self.user_metadatas.get(uploaded_by, [])}
        
        for chunk in chunks:
            chunk_id = f"{uploaded_by}-{hashlib.md5(chunk.encode()).hexdigest()}"
            if chunk_id not in user_chunk_hashes:
                user_chunk_hashes.add(chunk_id)
                unique_chunks.append(chunk)

        if not unique_chunks:
            print(f"⚠️ All chunks already exist for user '{uploaded_by}'")
            return

        embeddings = self._get_embeddings(unique_chunks)
        base_meta = metadata or {"source": "unknown"}
        meta_list = [
            {
                "text": chunk,
                "source": base_meta.get("source", "unknown"),
                "chunk_id": f"{uploaded_by}-{hashlib.md5(chunk.encode()).hexdigest()}",
                "uploaded_by": uploaded_by,
            }
            for chunk in unique_chunks
        ]

        # 1. Save to Cloud (Supabase + Qdrant)
        if self.use_cloud:
            success, msg = cloud_storage.save_document(
                filename=base_meta.get("source", "unknown"),
                content_hash=content_hash,
                content=content,
                size_mb=len(content.encode("utf-8")) / (1024 * 1024),
                uploaded_by=uploaded_by,
                is_safe=True,
                scan_issues=[],
            )
            if success:
                doc_result = cloud_storage.supabase.table("documents").select("id").eq("file_hash", f"{uploaded_by}_{content_hash}").execute()
                document_id = doc_result.data[0]['id'] if doc_result.data else str(uuid.uuid4())
                cloud_storage.store_vectors(embeddings=embeddings, metadatas=meta_list, document_id=document_id, uploaded_by=uploaded_by)
                print(f"✅ Saved to Cloud for '{uploaded_by}'")
            else:
                print(f"❌ Failed to save to cloud: {msg}")
                return

        # 2. Save to Local FAISS for this user (Fast!)
        faiss_store = self._get_user_faiss(uploaded_by)
        embeddings_np = np.array(embeddings).astype('float32')
        faiss_store.add(embeddings_np, meta_list)
        
        if uploaded_by not in self.user_corpuses:
            self.user_corpuses[uploaded_by] = []
            self.user_metadatas[uploaded_by] = []
        self.user_corpuses[uploaded_by].extend(unique_chunks)
        self.user_metadatas[uploaded_by].extend(meta_list)
        print(f"✅ Saved {len(unique_chunks)} chunks to local FAISS for '{uploaded_by}'")

    def remove_document_from_memory(self, doc_id_or_filename: str, username: str):
        """Remove document from local FAISS and memory for a specific user."""
        if username not in self.user_metadatas:
            return
            
        # Filter out the deleted document
        original_count = len(self.user_metadatas[username])
        new_metas = [m for m in self.user_metadatas[username] if m.get("chunk_id") != doc_id_or_filename and m.get("source") != doc_id_or_filename]
        
        if len(new_metas) < original_count:
            self.user_metadatas[username] = new_metas
            self.user_corpuses[username] = [m["text"] for m in new_metas if "text" in m]
            
            # Rebuild FAISS index (FAISS doesn't support easy deletion)
            new_faiss = FAISSStore(dim=384)
            if new_metas:
                texts = [m["text"] for m in new_metas if "text" in m]
                embeddings = self._get_embeddings(texts)
                embeddings_np = np.array(embeddings).astype('float32')
                new_faiss.add(embeddings_np, new_metas)
            self.user_faiss[username] = new_faiss
            print(f"🗑️ Rebuilt local FAISS for '{username}' after deletion.")

    def search(self, query: str, uploaded_by: str = "admin", top_k: int = 5) -> List[Dict]:
        # 1. Try Local FAISS first (Blazing Fast!)
        if uploaded_by in self.user_faiss and len(self.user_corpuses.get(uploaded_by, [])) > 0:
            faiss_store = self.user_faiss[uploaded_by]
            try:
                query_embedding = self._get_embeddings([query])[0]
                query_emb_np = np.array([query_embedding]).astype('float32')
                results = faiss_store.search(query_emb_np, top_k)
                return [
                    {
                        "text": r["metadata"].get("text", ""), 
                        "source": r["metadata"].get("source", "unknown"), 
                        "score": r["distance"], 
                        "chunk_id": r["metadata"].get("chunk_id")
                    } 
                    for r in results
                ]
            except Exception as e:
                print(f"❌ Local FAISS search failed for '{uploaded_by}': {e}")
                
        # 2. Fallback to Cloud
        if self.use_cloud:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_embedding = self._get_embeddings([query])[0]
                results = cloud_storage.qdrant.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=query_embedding,
                    query_filter=Filter(must=[FieldCondition(key="uploaded_by", match=MatchValue(value=uploaded_by))]),
                    limit=top_k
                )
                return [
                    {
                        "text": hit.payload.get("text", ""), 
                        "source": hit.payload.get("source", "unknown"), 
                        "score": hit.score,
                        "chunk_id": hit.payload.get("chunk_id")
                    } 
                    for hit in results
                ]
            except Exception as e:
                print(f"❌ Cloud search failed: {e}")
        return []

    def retrieve(self, query: str, k: int = 5, username: str = None) -> List[Dict]:
        """Wrapper for search that returns context with text."""
        target_user = username or self.current_user or "admin"
        return self.search(query, uploaded_by=target_user, top_k=k)

    def generate(self, query: str, context: List[Dict]) -> str:
        """Generate answer using flan-t5-large based on context."""
        try:
            from models.model_manager import ModelManager
            import torch
            mm = ModelManager()
            generator = mm.get_generator()
            tokenizer = generator["tokenizer"]
            model = generator["model"]
            device = generator["device"]
            context_text = "\n".join([f"- {c.get('text', '')}" for c in context[:3]])
            prompt = f"""Answer the question based only on the provided context.
Context:
{context_text}
Question: {query}
Answer:"""
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=150, temperature=0.7, do_sample=True, pad_token_id=tokenizer.eos_token_id)
            response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            return response if response else "I couldn't find a suitable answer in the provided documents."
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return "An error occurred while generating the response."

# Global instance
rag_service = RAGService()
