#!/bin/bash
set -e

# Wait for the database to be available
/app/wait-for-it.sh db:5432 -- echo "DB is ready"

python manage.py migrate --noinput

# Collect static files for serving via WhiteNoise/gunicorn
if [ "${SKIP_COLLECTSTATIC:-false}" != "true" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"