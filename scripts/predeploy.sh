#!/bin/bash
# Pre-deploy script for Render
# Runs migrations, collects static files, and seeds AI prompts

echo "Running database migrations..."
python manage.py migrate --run-syncdb || python manage.py migrate --fake-initial || echo "Migration issues detected, continuing..."

set -e  # Exit on any error for remaining commands

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Seeding AI prompts..."
python manage.py seed_ai_prompts

echo "Pre-deploy complete!"
