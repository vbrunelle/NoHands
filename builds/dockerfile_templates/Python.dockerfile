# Python Application Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy application code
COPY . .

# Expose the application port
EXPOSE 8080

# Default command
CMD ["python", "-m", "http.server", "8080"]
