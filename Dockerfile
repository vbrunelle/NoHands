# Dockerfile for NoHands - Django-based Docker image build automation server
#
# This Dockerfile creates a container to run the NoHands server.
# For production use, configure environment variables and use a production-ready
# database like PostgreSQL.

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# - git: Required for GitPython to clone and manage repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for temporary Git checkouts
RUN mkdir -p tmp/git_checkouts/cache tmp/git_checkouts/builds

# Expose port
EXPOSE 8000

# Default command: Run database migrations and start the server
# For production, use gunicorn instead of Django's development server
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
