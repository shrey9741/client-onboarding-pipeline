# Client Onboarding Pipeline -- API service
FROM python:3.11-slim

WORKDIR /app

# System deps for faiss / pdfplumber's underlying libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# .env is mounted or passed via --env-file at `docker run` time, not baked into the image
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
