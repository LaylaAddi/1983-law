#!/bin/bash
# Pre-deploy script for Render
# Runs migrations and seeds AI prompts

set -e  # Exit on any error

echo "Running database migrations..."
python manage.py migrate

echo "Seeding AI prompts..."
python manage.py seed_ai_prompts

echo "Pre-deploy complete!"
