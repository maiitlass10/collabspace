#!/bin/sh
# Apply database migrations, then start Daphne (one process: the live Yjs
# rooms are kept in this process's memory, see docs/DEPLOYMENT.md).
set -e
python manage.py migrate --noinput
exec daphne --bind 0.0.0.0 --port 8000 --proxy-headers config.asgi:application
