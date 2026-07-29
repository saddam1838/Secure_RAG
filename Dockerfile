FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

# Copy application code
COPY . .

# CRITICAL: Pass HF_TOKEN as a build argument to download gated models (e.g., Prompt-Guard)
ARG HF_TOKEN
ENV HF_TOKEN=$HF_TOKEN

# Pre-download models during build to speed up container startup
RUN python -c "from models.model_manager import ModelManager; ModelManager()"

CMD ["python", "app.py"]