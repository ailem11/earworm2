FROM python:3.13-slim

# Install system dependencies if any are needed (minimal image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install via pip
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend source files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Set working directory to backend where app.py is located
WORKDIR /app/backend

# Cloud Run binds to $PORT dynamically. Fallback to 8080.
ENV PORT=8080

# Serve using Gunicorn for production
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app --log-level debug"]
