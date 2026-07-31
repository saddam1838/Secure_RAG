FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p logs data index reports && \
    chmod -R 777 logs data index reports

# Pre-download models during build
ARG HF_TOKEN
ENV HF_TOKEN=$HF_TOKEN
RUN python -c "from models.model_manager import ModelManager; ModelManager()"

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI backend
CMD ["python", "app.py"]
