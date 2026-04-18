FROM python:3.11-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build so it is
# cached inside the image and does NOT need a network call at runtime.
# Without this, the first WebSocket connection would hang for ~30-60s
# while downloading ~90 MB from HuggingFace.
RUN python -c "
from chromadb.utils import embedding_functions
embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
print('Model cached successfully')
"

# Copy project
COPY . .

# Expose backend port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
