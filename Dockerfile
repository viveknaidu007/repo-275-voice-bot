# syntax=docker/dockerfile:1

# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libportaudio2 \
    portaudio19-dev \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first (for better caching)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip wheel setuptools && \
    pip install -r requirements.txt

# Copy application source
COPY . .

# Expose the port Render will map
EXPOSE 10000

# Render sets $PORT; default to 10000 locally
ENV PORT=10000 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Health check (optional but useful)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${PORT}/_stcore/health || exit 1

# Start the Streamlit app
CMD ["sh", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]
