# Django Application Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Allow connections from any host (development only)
ENV DJANGO_ALLOWED_HOSTS=*
# Disable strict security checks for development
ENV DEBUG=True

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir django

# Copy application code
COPY . .

# Create entrypoint script
RUN echo '#!/bin/sh\n\
set -e\n\
echo "Running database migrations..."\n\
python manage.py migrate --noinput || echo "Migration failed, continuing..."\n\
echo "Starting Django server..."\n\
exec python manage.py runserver 0.0.0.0:8000 --noreload\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput || true

# Expose the application port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
