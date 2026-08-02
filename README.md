<div align="center">

# 🔐 Enterprise Secure RAG

### A Secure Retrieval-Augmented Generation (RAG) Platform with Multi-Layer AI Security

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Enterprise Secure RAG** is a secure Retrieval-Augmented Generation (RAG) platform that protects Large Language Models (LLMs) from prompt injection attacks while providing accurate, citation-based responses from uploaded documents.

</div>

---

# 📖 Overview

Enterprise Secure RAG combines modern AI technologies with enterprise-grade security to build safe and reliable LLM applications. The platform enables secure document ingestion, semantic search, and intelligent question answering while applying multiple security layers to defend against prompt injection and malicious inputs.

Whether deployed locally or in the cloud, the platform is designed to provide a secure and scalable foundation for enterprise AI applications.

---

# ✨ Features

- 🔒 Multi-layer Prompt Injection Detection
- 📄 Secure Document Upload & Indexing
- 🤖 Hybrid RAG Pipeline
- 🔍 Attack Simulator
- 📊 Security Dashboard
- 📚 Citation-Based Responses
- 👤 JWT Authentication
- 📝 Audit Logging
- ☁️ Local & Cloud Storage Support
- 🐳 Docker Deployment

---

# 🏗️ System Architecture

```text
                    React Frontend
                           │
                           ▼
                   FastAPI REST API
                           │
      ┌────────────────────┼────────────────────┐
      ▼                    ▼                    ▼
 Authentication      Security Layer      RAG Pipeline
      │                    │                    │
      └────────────────────┼────────────────────┘
                           ▼
          Vector Database (Qdrant / FAISS)
                           │
                           ▼
              PostgreSQL / Supabase
```

---

# 🛡️ Security Pipeline

```text
User Query
     │
     ▼
Regex Validation
     │
     ▼
ML Prompt Injection Detection
     │
     ▼
LLM Safety Validation
     │
     ▼
Hybrid Document Retrieval
     │
     ▼
Response Generation
     │
     ▼
Output Guardrails
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
| Database | PostgreSQL, Supabase |
| Vector Database | Qdrant, FAISS |
| Authentication | JWT |
| Cache | Redis |
| Embeddings | Sentence Transformers |
| Language Model | FLAN-T5 |
| Deployment | Docker & Docker Compose |

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
├── tests/
├── docs/
│
├── app.py
├── config.py
├── database.py
├── document_scanner.py
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🚀 Quick Start

### Clone the Repository

```bash
git clone https://github.com/saddam1838/saddam1838-secure_rag.git

cd saddam1838-secure_rag
```

### Configure Environment

Copy the example environment file.

```bash
cp .env.example .env
```

Edit the `.env` file and update the required values.

### Example `.env.example`

```env
# ==========================================
# Enterprise Secure RAG - Environment Configuration
# ==========================================
# Copy this file to .env and fill in your actual values.
# NEVER commit the real .env file to version control!

# 1. CORE SECURITY & AUTHENTICATION
SECRET_KEY=change-me-to-a-random-32-character-string-in-production
BCRYPT_HASH=

# 2. CLOUD STORAGE
USE_CLOUD_STORAGE=false

# Qdrant Cloud
QDRANT_URL=https://your-cluster-url.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key-here
QDRANT_COLLECTION=rag_documents

# Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-key

# 3. Hugging Face
HF_TOKEN=

# 4. Security Settings
MAX_DOCUMENT_SIZE_MB=2
MAX_QUERY_LENGTH=2000
ML_PROMPT_INJECTION_THRESHOLD=0.85
```

### Start the Application

```bash
docker compose up --build
```

### Access the Platform

| Service | URL |
|----------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

# 📊 Core Modules

- 💬 Secure Chat Interface
- 📂 Document Upload & Management
- 🔍 Semantic Search
- 🤖 Hybrid RAG Engine
- 🛡️ Prompt Injection Detection
- ⚔️ Attack Simulator
- 📊 Security Dashboard
- 📜 Audit Logs

---

# 🔒 Security Features

- Multi-layer prompt injection defense
- Secure document scanning
- JWT authentication
- Role-based access control
- Query validation
- Output guardrails
- Audit logging
- Configurable security policies
- Local & cloud deployment support

---

# 📦 Deployment

The application supports multiple deployment options:

- Docker & Docker Compose
- Local Development
- Qdrant Cloud
- Supabase Cloud
- Local SQLite + FAISS

---

# 📈 Roadmap

- ✅ Secure RAG Pipeline
- ✅ Authentication & Authorization
- ✅ Document Upload & Indexing
- ✅ Prompt Injection Detection
- ✅ Security Dashboard
- ✅ Attack Simulator
- ⏳ Kubernetes Deployment
- ⏳ CI/CD Pipeline
- ⏳ Multi-Tenant Support

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch.

```bash
git checkout -b feature/my-feature
```

3. Commit your changes.

```bash
git commit -m "Add new feature"
```

4. Push your branch.

```bash
git push origin feature/my-feature
```

5. Open a Pull Request.

---

# 📄 License

This project is licensed under the **MIT License**.

---

# 🙏 Acknowledgements

This project is built using several excellent open-source technologies:

- FastAPI
- React
- Docker
- Qdrant
- FAISS
- Supabase
- Hugging Face
- Sentence Transformers

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a star on GitHub!

Built with ❤️ using **FastAPI**, **React**, **Docker**, and modern **AI Security** technologies.

</div>
