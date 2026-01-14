#!/usr/bin/env bash
set -e

echo "Running migrations..."
python manage.py makemigrations accounts documents --noinput || true
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} config.wsgi:application
