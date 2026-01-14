#!/usr/bin/env bash
set -e

echo "Running migrations..."
python manage.py makemigrations accounts documents --noinput || true
python manage.py migrate --noinput

echo "Testing Django imports..."
python -c "import django; django.setup(); from config.wsgi import application; print('WSGI app loaded successfully')"

echo "PORT is: $PORT"
echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --log-level debug --capture-output config.wsgi:application
