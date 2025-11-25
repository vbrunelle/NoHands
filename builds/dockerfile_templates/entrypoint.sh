#!/bin/sh
set -e

# Configure CSRF trusted origins if provided
if [ -n "$CSRF_TRUSTED_ORIGINS" ]; then
    echo "Configuring CSRF trusted origins: $CSRF_TRUSTED_ORIGINS"
    python /configure_csrf.py
fi

echo "Running database migrations..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000 --noreload
