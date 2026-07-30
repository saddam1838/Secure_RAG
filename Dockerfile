FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (including build-essential for compiling C extensions like pytrec_eval)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

# Copy application code
COPY . .

# CRITICAL: Pass HF_TOKEN as a build argument to download gated models
ARG HF_TOKEN
ENV HF_TOKEN=$HF_TOKEN

# Pre-download models during build to speed up container startup
RUN python -c "from models.model_manager import ModelManager; ModelManager()"

CMD ["python", "app.py"]
