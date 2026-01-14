FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --clear || true

# Expose port (Render uses $PORT env var, typically 10000)
EXPOSE 10000

# Run the application with gunicorn (use $PORT for Render compatibility)
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} config.wsgi:application
