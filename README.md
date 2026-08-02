<div align="center">

# 🔐 Enterprise Secure RAG

### A Secure Retrieval-Augmented Generation (RAG) Platform with Multi-Layer AI Security

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Hugging Face](https://img.shields.io/badge/HuggingFace-Models-FFD21E?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Enterprise Secure RAG** is a production-ready Retrieval-Augmented Generation (RAG) platform that combines semantic search with multi-layer AI security to defend against prompt injection attacks, malicious documents, and unsafe model outputs.

</div>

---

# 📖 Overview

Enterprise Secure RAG enables users to securely upload documents, build a searchable knowledge base, and interact with Large Language Models through a protected RAG pipeline. The platform integrates document scanning, prompt injection detection, semantic retrieval, reranking, and output validation to deliver secure and reliable AI responses.

---

# ✨ Features

- 🔒 Multi-layer Prompt Injection Detection
- 📄 Secure Document Upload & Processing
- 🤖 Hybrid Retrieval-Augmented Generation (RAG)
- 🔍 Semantic Search & Cross-Encoder Reranking
- 🛡️ AI Output Guardrails
- 📚 Citation-Based Responses
- 👤 JWT Authentication
- 📊 Security Dashboard
- 📝 Audit Logging
- ☁️ FAISS & Qdrant Support
- 🐳 Docker Deployment

---

# 🏗️ Architecture

```text
                 React Frontend
                        │
                        ▼
                FastAPI REST API
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
 Authentication   Security Layer   RAG Pipeline
        │               │               │
        └───────────────┼───────────────┘
                        ▼
        Vector Database (FAISS / Qdrant)
                        │
                        ▼
           PostgreSQL / Supabase
```

---

# 🤖 AI Models Used

| Model | Purpose |
|------|---------|
| **sentence-transformers/all-MiniLM-L6-v2** | Dense document and query embeddings |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Semantic reranking of retrieved documents |
| **google/flan-t5-large** | Response generation |
| **meta-llama/Prompt-Guard-86M** | Primary prompt injection detection |
| **ProtectAI/deberta-v3-base-prompt-injection-v2** | Fallback prompt injection detector |
| **unitary/toxic-bert** | Toxicity detection and output filtering |

### AI Pipeline

```text
User Query
     │
     ▼
Prompt Injection Detection
     │
     ▼
Embedding Generation
     │
     ▼
Vector Search
     │
     ▼
Cross-Encoder Reranking
     │
     ▼
FLAN-T5 Response Generation
     │
     ▼
Toxicity Filtering
     │
     ▼
Secure Response
```

---

# ⚙️ Technology Stack

| Category | Technologies |
|----------|--------------|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI, Python |
| Authentication | JWT |
| Database | PostgreSQL, Supabase |
| Vector Database | FAISS, Qdrant |
| AI Framework | Hugging Face Transformers |
| Deployment | Docker, Docker Compose |

---

# 📂 Project Structure

```text
enterprise-secure-rag/
│
├── api/
├── services/
├── models/
├── ui-react/
├── utils/
├── docs/
├── tests/
│
├── app.py
├── config.py
├── database.py
├── document_scanner.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🚀 Quick Start

### Clone the Repository

```bash
git clone [https://github.com/saddam1838/saddam1838-secure_rag.git](https://github.com/saddam1838/Secure_RAG.git)

cd Secure_RAG
```

### Configure Environment

```bash
cp .env.example .env
```

Update the required environment variables inside `.env`.

### Example `.env.example`

```env
SECRET_KEY=change-me-to-a-random-32-character-string

USE_CLOUD_STORAGE=false

QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=rag_documents

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

HF_TOKEN=

MAX_DOCUMENT_SIZE_MB=2
MAX_QUERY_LENGTH=2000
ML_PROMPT_INJECTION_THRESHOLD=0.85
```

### Start the Application

```bash
docker compose up --build
```

### Access the Application

| Service | URL |
|----------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

# 🛡️ Security Features

- Prompt Injection Detection
- Document Security Scanning
- Query Validation
- Toxic Output Filtering
- JWT Authentication
- Role-Based Access Control
- Audit Logging
- Configurable Security Policies

---

# 📦 Deployment

Supported deployment options:

- Docker & Docker Compose
- Local Development
- FAISS (Local)
- Qdrant Cloud
- PostgreSQL / Supabase

---

# 🗺️ Roadmap

- ✅ Secure RAG Pipeline
- ✅ Authentication & Authorization
- ✅ Prompt Injection Detection
- ✅ Document Upload & Retrieval
- ✅ Security Dashboard
- ⏳ Kubernetes Deployment
- ⏳ CI/CD Pipeline
- ⏳ Multi-Tenant Support

---

# 🤝 Contributing

Contributions are welcome!

```bash
# Fork the repository

git checkout -b feature/my-feature

git commit -m "Add new feature"

git push origin feature/my-feature
```

Open a Pull Request describing your changes.

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 🙏 Acknowledgements

This project is built using:

- FastAPI
- React
- Docker
- Hugging Face Transformers
- Sentence Transformers
- FAISS
- Qdrant
- Supabase

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a Star!

Built with ❤️ using **FastAPI**, **React**, **Docker**, and modern **AI Security** technologies.

</div>
