import hashlib
import pickle
import faiss
import numpy as np
import torch
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from models.model_manager import ModelManager
from models.vector_store import FAISSStore
from config import settings
from utils.helpers import tokenize, count_tokens, truncate_text
from services.cloud_storage import cloud_storage
import traceback


class RAGService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.mm = ModelManager()
        self.embed_model = self.mm.get_embedder()
        self.reranker = self.mm.get_reranker()
        self.generator = self.mm.get_generator()
        self.use_cloud = cloud_storage.is_cloud_enabled

        self.vector_store: Optional[FAISSStore] = None
        self.metadata: List[Dict] = []
        self.corpus: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.processed_hashes = set()
        self.chunk_hashes = set()
        self.embedding_cache = {}

        if self.use_cloud:
            self._load_from_cloud()
        else:
            self.load()

    def _load_from_cloud(self):
        docs = cloud_storage.get_all_safe_documents()
        print(f"📥 Loading {len(docs)} documents from cloud storage...")
        for doc in docs:
            try:
                chunks = self._chunk_document(doc.get("content", ""))
                uploader = doc.get("uploaded_by", "unknown")
                for chunk in chunks:
                    h = hashlib.md5(chunk.encode()).hexdigest()
                    key = (h, uploader)
                    if key not in self.chunk_hashes:
                        self.chunk_hashes.add(key)
                        self.corpus.append(chunk)
                        self.metadata.append({
                            "text": chunk,
                            "source": doc.get("filename", "unknown"),
                            "chunk_id": f"{uploader}-{h}",
                            "uploaded_by": uploader,
                        })
            except Exception as e:
                print(f"⚠️ Failed to process doc {doc.get('filename')}: {e}")
        if self.corpus:
            self.tokenized_corpus = [tokenize(doc) for doc in self.corpus]
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        print(f"✅ Loaded {len(self.corpus)} chunks for BM25 search")

    def remove_document_from_memory(self, source_filename: str):
        indices_to_remove = [
            i for i, meta in enumerate(self.metadata)
            if meta.get("source") == source_filename
        ]
        if not indices_to_remove:
            return False
        for i in sorted(indices_to_remove, reverse=True):
            chunk = self.corpus[i]
            h = hashlib.md5(chunk.encode()).hexdigest()
            user = self.metadata[i].get("uploaded_by", "unknown")
            self.chunk_hashes.discard((h, user))
            del self.corpus[i]
            del self.metadata[i]
            del self.tokenized_corpus[i]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None
        return True

    def _chunk_document(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " "],
        )
        return splitter.split_text(text)

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norms

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        cache_key = hashlib.md5("".join(texts).encode()).hexdigest()
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        emb = self.embed_model.encode(texts, convert_to_numpy=True)
        emb = self._normalize_embeddings(emb)
        self.embedding_cache[cache_key] = emb
        return emb

    def add_document(self, content: str, metadata: Dict = None, uploaded_by: str = "admin"):
        # 🔥 CRITICAL FIX: Separate global content hash from user-specific DB hash
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
            success, msg = cloud_storage.save_document(
                filename=base_meta.get("source", "unknown"),
                content_hash=content_hash,
                content=content,
                size_mb=len(content.encode("utf-8")) / (1024 * 1024),
                uploaded_by=uploaded_by,
                is_safe=True,
                scan_issues=[],
            )
            if not success:
                print(f"❌ Failed to save to Supabase: {msg}")
                return

            user_specific_hash = f"{uploaded_by}_{content_hash}"
            res = (
                cloud_storage.supabase.table("documents")
                .select("id")
                .eq("file_hash", user_specific_hash)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not res.data:
                print("❌ Could not retrieve document ID from Supabase")
                return
            supabase_id = res.data[0]["id"]

            cloud_storage.store_vectors(
                embeddings=embeddings.tolist(),
                metadatas=meta_list,
                document_id=supabase_id,
                uploaded_by=uploaded_by,
            )
            print(f"✅ Successfully saved and vectorized document for user '{uploaded_by}'")
        else:
            if self.vector_store is None:
                self.vector_store = FAISSStore(dim=embeddings.shape[1])
            self.vector_store.add(embeddings, meta_list)

        self.metadata.extend(meta_list)
        self.corpus.extend(unique_chunks)
        self.tokenized_corpus = [tokenize(doc) for doc in self.corpus]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        if not self.use_cloud:
            self.processed_hashes.add(content_hash)
            self.save()

    def retrieve(self, query: str, filters: Dict = None, k: int = None, username: str = None) -> List[Dict]:
        if k is None:
            k = settings.TOP_K_DENSE

        try:
            query_emb = self._get_embeddings([query])
            if self.use_cloud:
                # 🔥 FIX: Allows username=None for dashboard warm-up without crashing
                dense_docs = cloud_storage.search_vectors(query_embedding=query_emb[0].tolist(), k=k, uploaded_by=username)
            else:
                if self.vector_store is None or self.vector_store.index.ntotal == 0:
                    return []
                dense_results = self.vector_store.search(query_emb, k)
                if username:
                    dense_docs = [r["metadata"] for r in dense_results if r["metadata"].get("uploaded_by") == username]
                else:
                    dense_docs = [r["metadata"] for r in dense_results]

            if filters:
                dense_docs = [d for d in dense_docs if all(d.get(fk) == fv for fk, fv in filters.items())]
            return dense_docs[:k]
        except Exception as e:
            print(f"❌ retrieve() failed: {e}")
            return []

    def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        if not documents:
            return []
        pairs = [[query, doc["text"]] for doc in documents]
        scores = self.reranker.predict(pairs)
        sorted_indices = np.argsort(scores)[::-1]
        return [documents[i] for i in sorted_indices[: settings.TOP_K_RERANK]]

    def generate(self, query: str, context: List[Dict]) -> str:
        if not context:
            return "No relevant documents found in your knowledge base. Please upload documents to get started."
        context_text = "\n\n".join([f"Document {i + 1}:\n{c['text']}" for i, c in enumerate(context)])
        citations = [f"[{i}] {os.path.basename(c['source'])}" for i, c in enumerate(context, 1)]
        
        prompt = f"Answer based ONLY on the provided context.\n\nQuestion: {query}\nContext:\n{context_text}\nAnswer:"
        
        try:
            tokenizer = self.generator["tokenizer"]
            model = self.generator["model"]
            device = self.generator["device"]
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024).to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=300, temperature=0.2, do_sample=True, pad_token_id=tokenizer.eos_token_id)
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            return f"{generated_text}\n\n---\nSources: {' | '.join(citations)}"
        except Exception as e:
            return f"Generation unavailable: {str(e)}"

    def save(self):
        if self.use_cloud: return
        index_dir = settings.INDEX_DIR
        index_dir.mkdir(parents=True, exist_ok=True)
        if self.vector_store and hasattr(self.vector_store, "index"):
            faiss.write_index(self.vector_store.index, str(index_dir / "index.faiss"))
        with open(index_dir / "metadata.pkl", "wb") as f:
            pickle.dump(self.metadata, f)
        with open(index_dir / "corpus.pkl", "wb") as f:
            pickle.dump(self.corpus, f)
        with open(index_dir / "processed_hashes.pkl", "wb") as f:
            pickle.dump(self.processed_hashes, f)

    def load(self):
        if self.use_cloud: return
        index_dir = settings.INDEX_DIR
        if not index_dir.exists(): return
        if (index_dir / "index.faiss").exists():
            self.vector_store = FAISSStore(dim=384)
            self.vector_store.index = faiss.read_index(str(index_dir / "index.faiss"))
            with open(index_dir / "metadata.pkl", "rb") as f:
                self.metadata = pickle.load(f)
            self.vector_store.metadatas = self.metadata
            with open(index_dir / "corpus.pkl", "rb") as f:
                self.corpus = pickle.load(f)
                self.tokenized_corpus = [tokenize(doc) for doc in self.corpus]
                if self.tokenized_corpus:
                    self.bm25 = BM25Okapi(self.tokenized_corpus)
            if (index_dir / "processed_hashes.pkl").exists():
                with open(index_dir / "processed_hashes.pkl", "rb") as f:
                    self.processed_hashes = pickle.load(f)
