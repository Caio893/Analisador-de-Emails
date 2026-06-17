# VPS Deployment Guide

Target: Ubuntu 22.04 VPS with Docker and Docker Compose already installed.

This guide uses the production Docker Compose stack with Caddy in front. Only ports 80 and 443 should be public.

## 1. Point DNS

Create DNS records before starting the stack:

```text
email-radar.com      A      your-vps-ip
api.email-radar.com  A      your-vps-ip
```

Use the real production verification domain instead of placeholders.

## 2. Open Only Required Firewall Ports

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Do not open Postgres, Valkey, Django, or the frontend container ports publicly.

## 3. Copy The Project To The VPS

Use your normal Git or file-copy workflow. With Git, the shape is:

```bash
cd ~
git clone <your-repo-url> mailguard-ai
cd mailguard-ai
```

If the project is copied manually, make sure the VPS folder contains `docker-compose.prod.yml`, `backend/`, `frontend/`, `caddy/`, and `.env.production.example`.

## 4. Create Production Environment File

```bash
cp .env.production.example .env.production
nano .env.production
```

Minimum values to replace:

```env
SECRET_KEY=replace-with-a-long-random-django-secret-key
ALLOWED_HOSTS=email-radar.com,api.email-radar.com
BACKEND_URL=https://email-radar.com
FRONTEND_URL=https://email-radar.com
CORS_ALLOWED_ORIGINS=https://email-radar.com
CSRF_TRUSTED_ORIGINS=https://email-radar.com,https://api.email-radar.com
FRONTEND_SITE_ADDRESS=email-radar.com
API_SITE_ADDRESS=api.email-radar.com
BETA_BASIC_AUTH_USERNAME=replace-with-beta-user
BETA_BASIC_AUTH_PASSWORD=replace-with-beta-password
POSTGRES_PASSWORD=replace-with-a-strong-database-password
GOOGLE_CLIENT_ID=replace-with-google-oauth-client-id
GOOGLE_CLIENT_SECRET=replace-with-google-oauth-client-secret
GOOGLE_TOKEN_ENCRYPTION_KEY=replace-with-fernet-key-from-python-cryptography
GOOGLE_OAUTH_REDIRECT_URI=https://email-radar.com/api/auth/google/callback/
OPENAI_API_KEY=replace-with-openai-api-key
VITE_API_BASE_URL=https://email-radar.com/api
```

Keep these production values:

```env
DEBUG=false
OAUTHLIB_INSECURE_TRANSPORT=0
ALLOW_ACCOUNT_HEADER_AUTH=false
GMAIL_BODY_CHAR_LIMIT=6000
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
VITE_USE_MOCKS=false
ANALYSIS_QUEUE_ENABLED=true
OPENAI_DAILY_ANALYSIS_LIMIT=0
```

To generate a Django secret key without pasting one from a website:

```bash
python3 - <<'PY'
from secrets import token_urlsafe
print(token_urlsafe(50))
PY
```

To generate the OAuth token encryption key:

```bash
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Never commit `.env.production`.

## 5. Configure Google OAuth

In Google Cloud Console, configure the production OAuth client with:

```text
Authorized JavaScript origin:
https://email-radar.com

Authorized redirect URI:
https://email-radar.com/api/auth/google/callback/
```

Use only the Gmail readonly scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

## 6. Start The Production Stack

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Check status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Check logs if anything is still starting:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=120 caddy
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=120 backend
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=120 frontend
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=120 analysis-worker
```

Caddy will request HTTPS certificates automatically after DNS points to the VPS and ports 80 and 443 are reachable.

## 7. Smoke Test

From your computer:

```bash
curl -I https://email-radar.com/
curl -u beta-user:beta-password https://email-radar.com/healthz
curl -u beta-user:beta-password https://email-radar.com/api/healthz/
curl -u beta-user:beta-password https://email-radar.com/api/summary/
```

Expected results:

- Without Basic Auth, the app returns `401 Unauthorized`.
- With Basic Auth, `/healthz` returns `ok`.
- With Basic Auth, `/api/healthz/` returns `{"status":"ok"}`.
- With Basic Auth, `/api/summary/` returns JSON.

Then open `https://email-radar.com` in a browser, enter the beta credentials, and test Google login.

## 8. Update Deployment Later

```bash
cd ~/mailguard-ai
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

## 9. Backup Before Risky Changes

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres pg_dump -U mailguard mailguard > mailguard-backup.sql
```

If you change `POSTGRES_USER` or `POSTGRES_DB`, replace `mailguard` in that command.

## 10. Stop Or Restart

Restart:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart
```

Stop:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

Do not use `down -v` unless you intentionally want to delete the database volume.
