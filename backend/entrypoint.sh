#!/bin/bash
set -e

# python manage.py migrate --noinput

# Collect static files for serving via WhiteNoise/gunicorn
python manage.py collectstatic --noinput

exec "$@"