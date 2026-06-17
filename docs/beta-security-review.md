# Closed Beta Security Review

Status: acceptable for a small closed beta after production secrets, DNS, HTTPS, and Google OAuth are configured correctly.

## Passed Checks

- `DEBUG=false` is in the production example.
- Django now requires `SECRET_KEY`, `ALLOWED_HOSTS`, and `POSTGRES_PASSWORD` when `DEBUG=false`.
- Caddy is the only intended public entrypoint on ports 80 and 443.
- Production Postgres and Valkey do not publish host ports.
- Backend and frontend host bindings default to `127.0.0.1`, so they are not public on the VPS.
- Frontend production serving uses nginx static files instead of the Vite dev server.
- Closed beta Basic Auth protects both frontend and backend API, with health endpoints kept available for container checks.
- CORS is restricted to the production app origin.
- Secure session and CSRF cookies are enabled in the production example.
- Google OAuth uses `https://www.googleapis.com/auth/gmail.readonly` only.
- Google access and refresh tokens stay in the backend database, are encrypted at rest when `GOOGLE_TOKEN_ENCRYPTION_KEY` is configured, and are not sent to the frontend.
- The OAuth browser redirect includes only `account` and `connected=1`.
- Production can disable account selection through `X-Mailguard-Account`; the backend then uses the Django session set during OAuth callback.
- Profile controls include local session disconnect, OAuth token revocation attempt, Google permissions link, and active local data deletion.
- OpenAI analysis has cache reuse, queue deduplication, retry handling, daily limits, and local heuristic fallback.
- No real OpenAI key, Google secret, Django secret, beta password, or database password was found in the project scan.

## Remaining Risks

- There is no real per-user application authentication yet. During beta, anyone with the shared Basic Auth credentials is trusted inside the app.
- The Django session binding is suitable for a closed beta, but a broad public launch should still add first-party user authentication and account ownership enforcement.
- Synced email data is stored in the Postgres volume. Restrict VPS shell access, protect backups, and avoid sharing database dumps.
- Email content may be sent to OpenAI for analysis. Beta users should know this before connecting Gmail.
- Django admin remains mounted at `/admin/`. It is behind Basic Auth, but it is still extra attack surface if a Django superuser exists.
- `SECURE_SSL_REDIRECT=false` is kept to avoid proxy and healthcheck surprises. Caddy should still redirect public HTTP to HTTPS when using real HTTPS site addresses.
- Closed beta Basic Auth is temporary. Use a strong password, share it only with testers, and rotate it after the beta.

## Before Inviting Testers

- Replace every placeholder in `.env.production`.
- Confirm `.env.production` is not committed.
- Confirm DNS points to the VPS.
- Confirm `https://email-radar.com` has a valid certificate.
- Confirm unauthenticated requests return `401 Unauthorized`.
- Confirm Google OAuth callback is exactly `https://email-radar.com/api/auth/google/callback/`.
- Confirm Google consent shows readonly Gmail access only.
- Confirm `GOOGLE_TOKEN_ENCRYPTION_KEY` is set and `ALLOW_ACCOUNT_HEADER_AUTH=false`.
- Confirm `docker compose --env-file .env.production -f docker-compose.prod.yml ps` shows healthy services.

## Recommended Next Improvements

- Add real user login and tie each Google account to an authenticated user.
- Disable or protect Django admin separately in production.
- Add database backup rotation before storing meaningful beta data.
- Add basic request logging and error monitoring once users are active.
