FROM python:3.11-slim

WORKDIR /app

# Install system deps for torch and pygame
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libsdl2-dev libsdl2-mixer-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for model weights and sqlite DB
RUN mkdir -p /app/weights /app/data /app/models

COPY . .

EXPOSE 5000

# Note: In production on the i5-12H node, use the appropriate Nvidia CUDA runtime image 
# explicitly for GPU acceleration if device binding is used.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
