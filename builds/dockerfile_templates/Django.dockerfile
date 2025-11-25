# Django Application Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir django gunicorn

# Copy application code
COPY . .

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput || true

# Expose the application port
EXPOSE 8000

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "config.wsgi:application"]
