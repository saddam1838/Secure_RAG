import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

env_path = Path(".env")
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path.absolute()}")


class Settings(BaseSettings):
    # Local paths (fallback)
    DATA_DIR: Path = Path("data")
    LOG_DIR: Path = Path("logs")
    REPORT_DIR: Path = Path("reports")
    INDEX_DIR: Path = Path("index")

    # Models
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    NLI_MODEL: str = "cross-encoder/nli-deberta-v3-base"
    GENERATION_MODEL: str = "google/flan-t5-large"
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")

    # RAG Settings
    TOP_K_DENSE: int = 30
    TOP_K_RERANK: int = 5
    TOP_K_BM25: int = 30
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    RETRIEVAL_K: int = 10

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BCRYPT_HASH: str = os.getenv("BCRYPT_HASH", "")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    REDIS_URL: str = "redis://redis:6379/0"

    # === NEW: Cloud Storage ===
    USE_CLOUD_STORAGE: bool = os.getenv("USE_CLOUD_STORAGE", "false").lower() == "true"

    # Qdrant Cloud
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "rag_documents")

    # Supabase
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

# Validate critical settings
if not settings.BCRYPT_HASH and not settings.USE_CLOUD_STORAGE:
    print("⚠️ BCRYPT_HASH not set. Using Supabase for auth instead.")

if settings.USE_CLOUD_STORAGE:
    missing = []
    if not settings.QDRANT_URL:
        missing.append("QDRANT_URL")
    if not settings.QDRANT_API_KEY:
        missing.append("QDRANT_API_KEY")
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if missing:
        raise ValueError(f"Cloud storage enabled but missing: {', '.join(missing)}")
    print("✅ Cloud storage enabled: Qdrant + Supabase")
else:
    print("✅ Local storage mode: SQLite + FAISS")
