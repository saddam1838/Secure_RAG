---
title: Enterprise Secure RAG
emoji: 🔐
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Enterprise Secure RAG

Production-grade Secure GenAI Platform with:
- Hybrid RAG (FAISS/BM25/Qdrant + CrossEncoder reranking)
- Multi-layer security (OWASP/MITRE/NIST compliant)
- Cloud persistence (Qdrant + Supabase)
- Real-time security posture scoring

## Architecture
- **Vector Storage**: Qdrant Cloud (or local FAISS fallback)
- **Metadata/Auth**: Supabase PostgreSQL (or local SQLite fallback)
- **Generation**: google/flan-t5-large
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Security**: ProtectAI/deberta-v3-base-prompt-injection-v2

## Default Credentials
- Username: `admin`
- Password: `admin123`