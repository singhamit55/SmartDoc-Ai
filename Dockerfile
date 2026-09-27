# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for torch, chromadb, and PDF libs
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Install torch CPU-only first (much smaller, no CUDA needed on HF free tier)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create persistent data directories
RUN mkdir -p /app/data/chroma /app/data/docs

# Embeddings are now downloaded via the Hugging Face Serverless API at runtime

# Expose the port HF Spaces expects
EXPOSE 7860

# Run the FastAPI app on the port provided by the host (default 7860)
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"
