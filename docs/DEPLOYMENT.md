# Deployment guide

CollabSpace ships as four containers (`docker-compose.yml`):

| Service | Image | Role | Exposed |
|---|---|---|---|
| `frontend` | nginx + the built React app | serves the app, forwards `/api`, `/ws`, `/admin`, `/static` to Django | **yes** (port `8080` by default) |
| `backend` | Python 3.14 + Daphne | Django REST API + Channels WebSocket | no |
| `db` | PostgreSQL 16 | data | no |
| `redis` | Redis 7 | channel layer (messages between consumers) | no |

## 1. Run it on any machine with Docker

```bash
git clone https://github.com/maiitlass10/collabspace.git
cd collabspace
cp .env.example .env        # then edit .env: set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
```

Open http://localhost:8080. Create an admin account (for `/admin/`):

```bash
docker compose exec backend python manage.py createsuperuser
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 2. Settings (`.env`)

| Variable | Example | Meaning |
|---|---|---|
| `DJANGO_SECRET_KEY` | long random string | **required**; never commit it |
| `POSTGRES_PASSWORD` | long random string | **required** |
| `SITE_URL` | `https://docs.example.com` | the address people open; trusted for CSRF |
| `DJANGO_ALLOWED_HOSTS` | `docs.example.com` | host names Django answers to (comma-separated) |
| `HTTP_PORT` | `8080` | port nginx listens on, on the host |
| `DJANGO_SECURE_COOKIES` | `True` behind HTTPS | session/CSRF cookies only over HTTPS |
| `DJANGO_BEHIND_HTTPS_PROXY` | `True` behind HTTPS | trust `X-Forwarded-Proto` from the proxy |

## 3. A real server with HTTPS

1. A small Linux server (1 vCPU / 1–2 GB RAM is enough to start) with Docker installed, and a domain pointing to it.
2. Put an HTTPS reverse proxy in front of port `8080`. With [Caddy](https://caddyserver.com/) the whole config is:

   ```
   docs.example.com {
       reverse_proxy localhost:8080
   }
   ```

   Caddy gets and renews the certificate itself, and forwards WebSockets automatically.
3. In `.env`: `SITE_URL=https://docs.example.com`, `DJANGO_ALLOWED_HOSTS=docs.example.com`,
   `DJANGO_SECURE_COOKIES=True`, `DJANGO_BEHIND_HTTPS_PROXY=True`.
4. `docker compose up -d --build`

## 4. Day-to-day operations

```bash
docker compose logs -f backend                    # logs
git pull && docker compose up -d --build          # update (migrations run on start)
docker compose exec db pg_dump -U collabspace collabspace > backup.sql   # backup
```

Restore a backup into an empty database:

```bash
docker compose exec -T db psql -U collabspace collabspace < backup.sql
```

## 5. Scaling: what works and what does not (yet)

- **One backend process is supported.** Each open document has a live Yjs "room"
  in the memory of the Daphne process (`collaboration/rooms.py`). It is saved
  2 seconds after the last edit and when the last person leaves.
- **Redis** carries Channels messages (for example "this user lost access, close
  their connection"), so REST requests and WebSockets do not have to share a
  process for that.
- **Several backend processes would each keep their own copy of a room**, so two
  people connected to different processes would not see each other's edits.
  Scaling out needs the Yjs state shared between processes (for example
  y-redis, or routing every document to one process). That is the next step,
  not something the current code does.
- A single Daphne process handles many simultaneous editors; most documents
  are small Yjs states.

## 6. Security checklist

- [x] `DJANGO_DEBUG=False` (set by `docker-compose.yml`)
- [x] Secrets only in `.env` (ignored by Git)
- [x] Only nginx is reachable from outside; Django, PostgreSQL and Redis stay on the private Docker network
- [x] Containers run Django as a non-root user
- [ ] HTTPS in front, with `DJANGO_SECURE_COOKIES=True` and `DJANGO_BEHIND_HTTPS_PROXY=True`
- [ ] Regular `pg_dump` backups copied off the server
