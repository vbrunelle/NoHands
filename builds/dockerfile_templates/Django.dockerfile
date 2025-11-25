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
# CSRF_TRUSTED_ORIGINS will be set at runtime by NoHands when starting the container
# This allows the containerized app to accept requests from the NoHands proxy

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

# Create CSRF configuration script
RUN echo 'import os' > /configure_csrf.py && \
    echo 'import glob' >> /configure_csrf.py && \
    echo '' >> /configure_csrf.py && \
    echo 'csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")' >> /configure_csrf.py && \
    echo 'if csrf_origins:' >> /configure_csrf.py && \
    echo '    origins = [o.strip() for o in csrf_origins.split(",") if o.strip()]' >> /configure_csrf.py && \
    echo '    settings_patterns = ["**/settings.py", "settings.py"]' >> /configure_csrf.py && \
    echo '    for pattern in settings_patterns:' >> /configure_csrf.py && \
    echo '        for settings_file in glob.glob(pattern, recursive=True):' >> /configure_csrf.py && \
    echo '            if "venv" not in settings_file and "site-packages" not in settings_file:' >> /configure_csrf.py && \
    echo '                try:' >> /configure_csrf.py && \
    echo '                    with open(settings_file, "a") as f:' >> /configure_csrf.py && \
    echo '                        f.write("\\n")' >> /configure_csrf.py && \
    echo '                        f.write("# Auto-configured by NoHands\\n")' >> /configure_csrf.py && \
    echo '                        f.write(f"CSRF_TRUSTED_ORIGINS = {origins}\\n")' >> /configure_csrf.py && \
    echo '                    print(f"Configured CSRF in {settings_file}: {origins}")' >> /configure_csrf.py && \
    echo '                    break' >> /configure_csrf.py && \
    echo '                except Exception as e:' >> /configure_csrf.py && \
    echo '                    print(f"Failed to update {settings_file}: {e}")' >> /configure_csrf.py

# Create entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'set -e' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Configure CSRF trusted origins if provided' >> /entrypoint.sh && \
    echo 'if [ -n "$CSRF_TRUSTED_ORIGINS" ]; then' >> /entrypoint.sh && \
    echo '    echo "Configuring CSRF trusted origins: $CSRF_TRUSTED_ORIGINS"' >> /entrypoint.sh && \
    echo '    python /configure_csrf.py' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo 'echo "Running database migrations..."' >> /entrypoint.sh && \
    echo 'python manage.py migrate --noinput || echo "Migration failed, continuing..."' >> /entrypoint.sh && \
    echo 'echo "Starting Django server..."' >> /entrypoint.sh && \
    echo 'exec python manage.py runserver 0.0.0.0:8000 --noreload' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput || true

# Expose the application port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
