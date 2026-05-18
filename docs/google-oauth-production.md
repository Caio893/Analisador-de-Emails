# Google OAuth Production Setup

Use one public app origin for the closed beta:

- App and API origin: `https://email-radar.com`
- OAuth callback URI: `https://email-radar.com/api/auth/google/callback/`

Keeping the callback on the same origin as the frontend lets Django keep the OAuth state in its secure session cookie without cross-site cookie surprises.

## Google Cloud Console

1. Open Google Cloud Console and select the Email Radar production project.
2. Enable the Gmail API for the project.
3. Configure the OAuth consent screen:
   - Use testing mode for closed beta.
   - Add only known beta tester Google accounts.
   - Add the production domain: `email-radar.com`.
4. Configure scopes:
   - Keep only `https://www.googleapis.com/auth/gmail.readonly`.
   - Do not add write or send scopes such as `gmail.modify`, `gmail.send`, or `https://mail.google.com/`.
5. Create or update an OAuth client:
   - Type: Web application.
   - Authorized JavaScript origins: `https://email-radar.com`.
   - Authorized redirect URIs: `https://email-radar.com/api/auth/google/callback/`.

Google requires the redirect URI to match exactly, including scheme, host, path, and trailing slash. Gmail readonly is still a restricted scope, so keep beta access small and expect extra Google review work before a broad public launch.

Official references:

- Google OAuth web server flow: https://developers.google.com/identity/protocols/oauth2/web-server
- Gmail API scopes: https://developers.google.com/workspace/gmail/api/auth/scopes

## VPS Environment

Set these values in `.env.production`:

```env
BACKEND_URL=https://email-radar.com
FRONTEND_URL=https://email-radar.com
CORS_ALLOWED_ORIGINS=https://email-radar.com
CSRF_TRUSTED_ORIGINS=https://email-radar.com
GOOGLE_CLIENT_ID=replace-with-google-oauth-client-id
GOOGLE_CLIENT_SECRET=replace-with-google-oauth-client-secret
GOOGLE_TOKEN_ENCRYPTION_KEY=replace-with-fernet-key-from-python-cryptography
GOOGLE_OAUTH_REDIRECT_URI=https://email-radar.com/api/auth/google/callback/
OAUTHLIB_INSECURE_TRANSPORT=0
ALLOW_ACCOUNT_HEADER_AUTH=false
GMAIL_BODY_CHAR_LIMIT=6000
VITE_API_BASE_URL=https://email-radar.com/api
VITE_API_WITH_CREDENTIALS=true
```

Generate `GOOGLE_TOKEN_ENCRYPTION_KEY` with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Do not put Google credentials, token encryption keys, Django secrets, database passwords, or OpenAI keys in the frontend, Dockerfile, Caddyfile, or Git. They should live only in `.env.production` on the VPS or in a managed secret store.

## Safety Checks

- The backend requests only the Gmail readonly scope.
- Google access and refresh tokens are stored only in the backend database and encrypted at rest by `GOOGLE_TOKEN_ENCRYPTION_KEY`.
- The callback redirects the browser with `account` and `connected=1` only.
- The frontend stores the connected email address locally, not Google tokens.
- Production backend account access uses the post-OAuth Django session, not a client-selected account header.
- Closed beta Basic Auth still protects the app and API before Google login.

## Manual Test

1. Visit `https://email-radar.com`.
2. Enter the closed beta Basic Auth credentials.
3. Start Google login.
4. Confirm Google shows only readonly Gmail access.
5. After redirect, confirm the URL is `/app/inbox?account=...&connected=1`.
6. Confirm there is no `code`, `access_token`, or `refresh_token` in the browser URL.
7. Run an inbox or spam sync and confirm emails load through the backend API.
