# CollabSpace backend: Django + Channels served by Daphne (HTTP + WebSocket).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --only-binary=:all: -r requirements.txt

COPY . .

# Admin CSS/JS, served by WhiteNoise. (The key is only needed to load settings.)
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

# Never run the app as root.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000
# Run through `sh`: works even if Git (e.g. on Windows) lost the executable bit.
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
