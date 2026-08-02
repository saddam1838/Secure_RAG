import hashlib
import uuid
import os
from typing import List, Dict, Optional
from services.cloud_storage import cloud_storage
from config import settings

class RAGService:
    def __init__(self):
        self.use_cloud = cloud_storage.is_cloud_enabled
        self.vector_store = None
        self.metadata = []
        self.processed_hashes = set()
        self.chunk_hashes = set()
        self.corpus = []  # Now a list for easy length checking and iteration
        self.current_user = None  # Will be set when user logs in
        
        if not self.use_cloud:
            try:
                from services.vector_store import LocalVectorStore
                self.vector_store = LocalVectorStore()
            except Exception as e:
                print(f"⚠️ Local vector store not available: {e}")

    def load_user_data(self, username: str):
        """Load all chunks for this user from Qdrant into local memory (corpus & metadata)."""
        if not self.use_cloud:
            return
        self.current_user = username
        print(f"🔄 Loading user data for '{username}' from Qdrant into local memory...")
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            from config import settings
            scroll_result = cloud_storage.qdrant.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                scroll_filter=Filter(
                    must=[FieldCondition(key="uploaded_by", match=MatchValue(value=username))]
                ),
                limit=10000,  # reasonable limit
                with_payload=True,
                with_vectors=False
            )
            points = scroll_result[0]
            if points:
                self.corpus = []
                self.metadata = []
                for p in points:
                    payload = p.payload
                    text = payload.get("text", "")
                    if text:
                        self.corpus.append(text)
                        self.metadata.append({
                            "chunk_id": payload.get("chunk_id", str(p.id)),
                            "source": payload.get("source", "unknown"),
                            "uploaded_by": payload.get("uploaded_by", "unknown"),
                            "text": text
                        })
                print(f"✅ Loaded {len(self.corpus)} chunks for user '{username}' into local memory.")
            else:
                self.corpus = []
                self.metadata = []
                print(f"ℹ️ No documents found for user '{username}' in cloud.")
        except Exception as e:
            print(f"⚠️ Failed to load user data from cloud: {e}")
            self.corpus = []
            self.metadata = []

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
            from services.embedder import embedder
            return embedder.encode(texts).tolist()
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return [[0.0] * 384 for _ in texts]

    def add_document(self, content: str, metadata: Dict = None, uploaded_by: str = "admin"):
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        exists = cloud_storage.document_exists_for_user(content_hash, uploaded_by)
        if self.use_cloud and exists:
            print(f"ℹ️ Document already exists for user '{uploaded_by}'")
            return
        if not self.use_cloud and content_hash in self.processed_hashes:
            return

        chunks = self._chunk_document(content)
        if not chunks:
            return

        unique_chunks = []
        for chunk in chunks:
            h = hashlib.md5(chunk.encode()).hexdigest()
            key = (h, uploaded_by)
            if key not in self.chunk_hashes:
                self.chunk_hashes.add(key)
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
                "category": base_meta.get("category", "general"),
                "chunk_id": f"{uploaded_by}-{hashlib.md5(chunk.encode()).hexdigest()}",
                "uploaded_by": uploaded_by,
            }
            for chunk in unique_chunks
        ]

        if self.use_cloud:
            print(f"☁️ Saving {len(unique_chunks)} chunks to CLOUD storage for '{uploaded_by}'")
            
            success, msg = cloud_storage.save_document(
                filename=base_meta.get("source", "unknown"),
                content_hash=content_hash,
                content=content,
                size_mb=len(content.encode("utf-8")) / (1024 * 1024),
                uploaded_by=uploaded_by,
                is_safe=True,
                scan_issues=[],
                chunk_count=len(unique_chunks),
            )

            if success:
                doc_result = cloud_storage.supabase.table("documents").select("id").eq("file_hash", f"{uploaded_by}_{content_hash}").execute()
                document_id = doc_result.data[0]['id'] if doc_result.data else str(uuid.uuid4())

                print(f"🔥 Storing {len(unique_chunks)} chunks in Qdrant...")
                cloud_storage.store_vectors(
                    embeddings=embeddings,
                    metadatas=meta_list,
                    document_id=document_id,
                    uploaded_by=uploaded_by
                )
                print(f"✅ SUCCESS: Saved to Supabase and {len(unique_chunks)} chunks to Qdrant.")
                # Also add to local memory for fast access
                self.corpus.extend(unique_chunks)
                self.metadata.extend(meta_list)
            else:
                print(f"❌ Failed to save to cloud: {msg}")
        else:
            print("💻 Saving to LOCAL storage")
            if self.vector_store:
                self.vector_store.add(unique_chunks, embeddings)
            self.metadata.extend(meta_list)
            self.processed_hashes.add(content_hash)
            self.corpus.extend(unique_chunks)  # local corpus as list
            print(f"✅ Saved {len(unique_chunks)} chunks to local memory")

    def remove_document_from_memory(self, filename: str):
        if not self.use_cloud:
            # For local storage, remove from metadata and corpus (if it's a dict)
            self.metadata = [m for m in self.metadata if m.get("source") != filename]
            # If corpus is a dict, remove key; if list, we need to filter by source? 
            # Actually for local we store as list, we'll filter by source in metadata and rebuild corpus.
            # But for simplicity, we'll just rely on metadata.
            # We'll keep it as list and filter when needed.
            # Since we may have used it as dict earlier, we'll handle both.
            if isinstance(self.corpus, dict):
                if filename in self.corpus:
                    del self.corpus[filename]
            elif isinstance(self.corpus, list):
                # We can't easily remove by filename because we don't store filename per chunk.
                # We'll rely on metadata filtering.
                pass
            print(f"🗑️ Removed {filename} from local memory")
        else:
            # For cloud, we just clear the loaded data and reload if needed.
            # But we can remove from current corpus/metadata by filtering.
            self.metadata = [m for m in self.metadata if m.get("source") != filename]
            # Rebuild corpus from remaining metadata
            self.corpus = [m["text"] for m in self.metadata if "text" in m]
            print(f"🗑️ Removed {filename} from local memory (cloud sync)")

    def search(self, query: str, uploaded_by: str = "admin", top_k: int = 5) -> List[Dict]:
        # Prefer local if available, else fallback to cloud
        if not self.use_cloud or (self.use_cloud and self.corpus and len(self.corpus) > 0):
            # Use local FAISS if we have a vector store and embeddings
            if self.vector_store:
                try:
                    query_embedding = self._get_embeddings([query])[0]
                    results = self.vector_store.search(query_embedding, top_k)
                    return [{"text": chunk, "source": meta.get("source", "unknown"), "score": score} for chunk, meta, score in results]
                except Exception as e:
                    print(f"❌ Local search failed, falling back to cloud: {e}")
            else:
                # If no vector store, but we have corpus, we could do simple keyword search? Not ideal.
                # Fallback to cloud.
                pass
        
        # Cloud fallback
        if self.use_cloud:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_embedding = self._get_embeddings([query])[0]
                
                results = cloud_storage.qdrant.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=query_embedding,
                    query_filter=Filter(
                        must=[FieldCondition(key="uploaded_by", match=MatchValue(value=uploaded_by))]
                    ),
                    limit=top_k
                )
                
                return [{"text": hit.payload.get("text", ""), "source": hit.payload.get("source", "unknown"), "score": hit.score} for hit in results]
            except Exception as e:
                print(f"❌ Cloud search failed: {e}")
                return []
        else:
            # No cloud, no local store
            return []

    def retrieve(self, query: str, k: int = 5, username: str = None) -> List[Dict]:
        """Wrapper for search that returns context with text."""
        return self.search(query, uploaded_by=username or self.current_user or "admin", top_k=k)

    def generate(self, query: str, context: List[Dict]) -> str:
        """Generate answer using flan-t5-large based on context."""
        try:
            from models.model_manager import ModelManager
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
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=150,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            return response if response else "I couldn't find a suitable answer in the provided documents."
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return "An error occurred while generating the response."

# Global instance
rag_service = RAGService()
