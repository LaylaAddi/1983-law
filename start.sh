#!/usr/bin/env bash

echo "=== Starting startup script ==="

echo "Running migrations..."
python manage.py makemigrations accounts documents --noinput || echo "makemigrations had issues"
python manage.py migrate --noinput || echo "migrate had issues"

echo "=== Migrations done ==="

echo "Seeding AI prompts..."
python manage.py seed_ai_prompts || echo "seed_ai_prompts had issues"

echo "=== Seeding done ==="

echo "Testing Django imports..."
python -c "import django; django.setup(); from config.wsgi import application; print('WSGI app loaded successfully')" || echo "Django import failed"

echo "PORT is: $PORT"
echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --timeout 120 --log-level debug --capture-output --access-logfile - --error-logfile - config.wsgi:application
