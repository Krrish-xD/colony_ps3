FROM public.ecr.aws/docker/library/python:3.11-slim

# IMPORTANT: For GPU support, the actual deployment should use nvidia/cuda:12.1.0-runtime-ubuntu22.04
# as base image instead, with `pip install torch --index-url https://download.pytorch.org/whl/cu121`.
# We keep python:3.11-slim as default for CPU-only development/testing.

WORKDIR /app

# Install system deps for torch
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY *.whl ./
RUN pip install --no-index --find-links . -r requirements.txt

COPY . .

# Create directories for model weights and fingerprint DB
RUN mkdir -p /app/weights /app/data

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
