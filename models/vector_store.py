import abc
import faiss
import numpy as np
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any


class VectorStore(abc.ABC):
    @abc.abstractmethod
    def add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        pass

    @abc.abstractmethod
    def search(self, query_emb: np.ndarray, k: int):
        pass


class FAISSStore(VectorStore):
    def __init__(self, dim: int, normalize: bool = True):
        self.dim = dim
        self.normalize = normalize
        self.index = faiss.IndexFlatIP(dim)
        self.metadatas = []

    def add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        if self.normalize:
            faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.metadatas.extend(metadatas)

    def search(self, query_emb: np.ndarray, k: int):
        if self.normalize:
            faiss.normalize_L2(query_emb)
        distances, indices = self.index.search(query_emb, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadatas):
                results.append(
                    {"distance": distances[0][i], "metadata": self.metadatas[idx]}
                )
            else:
                # skip out-of-range indices (should not happen if metadata sync)
                continue
        return results


class ChromaStore(VectorStore):
    def __init__(self, collection_name="rag", embedding_fn=None):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=embedding_fn
        )
        self.current_id = 0

    def add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        ids = [str(i) for i in range(self.current_id, self.current_id + len(metadatas))]
        self.current_id += len(metadatas)
        self.collection.add(
            embeddings=embeddings.tolist(), metadatas=metadatas, ids=ids
        )

    def search(self, query_emb: np.ndarray, k: int):
        results = self.collection.query(
            query_embeddings=query_emb.tolist(), n_results=k
        )
        return [
            {"distance": d, "metadata": m}
            for d, m in zip(results["distances"][0], results["metadatas"][0])
        ]
