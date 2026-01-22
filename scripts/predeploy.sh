#!/bin/bash
# Pre-deploy script for Render
# Runs migrations, collects static files, and seeds AI prompts

set -e  # Exit on any error

echo "Running database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Seeding AI prompts..."
python manage.py seed_ai_prompts

echo "Pre-deploy complete!"
