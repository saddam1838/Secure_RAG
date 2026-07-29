FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

COPY . .

# Pre-download models during build
RUN python -c "from models.model_manager import ModelManager; ModelManager()"

CMD ["python", "app.py"]