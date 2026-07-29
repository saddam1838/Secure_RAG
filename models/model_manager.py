import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from config import settings


class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._pi_detector = None
        self._embedder = None
        self._reranker = None
        self._generator = None

    def get_pi_detector(self):
        if self._pi_detector is None:
            print("🔄 Auto-loading Prompt Guard...")
            try:
                self._pi_detector = pipeline(
                    "text-classification",
                    model="meta-llama/Prompt-Guard-86M",
                    device=-1,
                )
            except Exception:
                print("⚠️ Fallback to ProtectAI/deberta-v3-base-prompt-injection-v2")
                self._pi_detector = pipeline(
                    "text-classification",
                    model="ProtectAI/deberta-v3-base-prompt-injection-v2",
                    device=-1,
                )
        return self._pi_detector

    def get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            model_name = getattr(
                settings, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            )
            print(f"🔄 Auto-loading Embedder: {model_name}...")
            self._embedder = SentenceTransformer(model_name)
        return self._embedder

    def get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            model_name = getattr(
                settings, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
            print(f"🔄 Auto-loading Reranker: {model_name}...")
            self._reranker = CrossEncoder(model_name)
        return self._reranker

    def get_generator(self):
        if self._generator is None:
            model_name = getattr(settings, "GENERATION_MODEL", "google/flan-t5-large")
            print(f"🔄 Auto-loading Generator: {model_name} (Optimized: float16)...")

            tokenizer = AutoTokenizer.from_pretrained(model_name)
            # AUTOMATIC MEMORY OPTIMIZATION: Halves RAM usage and prevents loading spikes
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, torch_dtype=torch.float16, low_cpu_mem_usage=True
            )

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            self._generator = {"tokenizer": tokenizer, "model": model, "device": device}

        return self._generator
