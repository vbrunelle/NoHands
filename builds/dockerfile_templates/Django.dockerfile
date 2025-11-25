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
# For development containers, we disable CSRF to avoid proxy-related issues
RUN echo 'import os' > /configure_csrf.py && \
    echo 'import glob' >> /configure_csrf.py && \
    echo 'import re' >> /configure_csrf.py && \
    echo '' >> /configure_csrf.py && \
    echo 'settings_patterns = ["**/settings.py", "settings.py"]' >> /configure_csrf.py && \
    echo 'for pattern in settings_patterns:' >> /configure_csrf.py && \
    echo '    for settings_file in glob.glob(pattern, recursive=True):' >> /configure_csrf.py && \
    echo '        if "venv" not in settings_file and "site-packages" not in settings_file:' >> /configure_csrf.py && \
    echo '            try:' >> /configure_csrf.py && \
    echo '                # Read the existing settings' >> /configure_csrf.py && \
    echo '                with open(settings_file, "r") as f:' >> /configure_csrf.py && \
    echo '                    content = f.read()' >> /configure_csrf.py && \
    echo '' >> /configure_csrf.py && \
    echo '                # Check if MIDDLEWARE is defined' >> /configure_csrf.py && \
    echo '                if "MIDDLEWARE" in content:' >> /configure_csrf.py && \
    echo '                    # Comment out CSRF middleware' >> /configure_csrf.py && \
    echo '                    content = re.sub(' >> /configure_csrf.py && \
    echo '                        r"([ ]*)(\"django.middleware.csrf.CsrfViewMiddleware\")",' >> /configure_csrf.py && \
    echo '                        r"\1# \2  # Disabled by NoHands for dev",' >> /configure_csrf.py && \
    echo '                        content' >> /configure_csrf.py && \
    echo '                    )' >> /configure_csrf.py && \
    echo '                    content = re.sub(' >> /configure_csrf.py && \
    echo '                        r"([ ]*)(\"django.middleware.csrf.CsrfViewMiddleware\")",' >> /configure_csrf.py && \
    echo '                        r"\1# \2  # Disabled by NoHands for dev",' >> /configure_csrf.py && \
    echo '                        content' >> /configure_csrf.py && \
    echo '                    )' >> /configure_csrf.py && \
    echo '' >> /configure_csrf.py && \
    echo '                # Write back' >> /configure_csrf.py && \
    echo '                with open(settings_file, "w") as f:' >> /configure_csrf.py && \
    echo '                    f.write(content)' >> /configure_csrf.py && \
    echo '                print(f"Disabled CSRF in {settings_file} for NoHands dev environment")' >> /configure_csrf.py && \
    echo '                break' >> /configure_csrf.py && \
    echo '            except Exception as e:' >> /configure_csrf.py && \
    echo '                print(f"Failed to update {settings_file}: {e}")' >> /configure_csrf.py

# Create entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'set -e' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Disable CSRF middleware for dev environment' >> /entrypoint.sh && \
    echo 'echo "Disabling CSRF protection for NoHands dev environment..."' >> /entrypoint.sh && \
    echo 'python /configure_csrf.py' >> /entrypoint.sh && \
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
