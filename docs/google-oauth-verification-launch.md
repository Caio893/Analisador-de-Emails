# Email Radar Google OAuth Verification Launch Runbook

Last updated: May 17, 2026

This runbook is for the production Google OAuth verification submission for
Email Radar at `https://email-radar.com/`.

## Verification posture

Email Radar currently uses:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Google classifies this as a restricted Gmail scope. Treat the launch as a
restricted-scope OAuth review, not a light brand-only review.

Google's May 2026 review email for project `561450909122`
(`custom-search-api-455516`) explicitly requires a CASA Tier 2 security
assessment by August 14, 2026. Start the CASA process immediately; the App
Defense Alliance notes that assessment timing can depend on assessor capacity
and application responsiveness.

Primary policy references:

- Google API Services User Data Policy:
  https://developers.google.com/terms/api-services-user-data-policy
- Google Workspace API User Data and Developer Policy:
  https://developers.google.com/workspace/workspace-api-user-data-developer-policy
- Gmail API scopes:
  https://developers.google.com/workspace/gmail/api/auth/scopes
- Restricted scope verification:
  https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- Sign in with Google branding:
  https://developers.google.com/identity/branding-guidelines
- CASA:
  https://appdefensealliance.dev/casa

## Must be true before submitting

- The production homepage is publicly reachable at `https://email-radar.com/`.
- The homepage clearly identifies Email Radar and describes the Gmail security
  analysis use case.
- The homepage links to:
  - `https://email-radar.com/privacy`
  - `https://email-radar.com/terms`
- The OAuth CTA is immediately preceded by an in-product disclosure describing:
  - Gmail read-only access.
  - Data categories processed.
  - Why the data is used.
  - AI analysis purpose.
  - No send/edit/delete capability.
- Users must affirmatively accept the disclosure before OAuth starts.
- The privacy policy contains this exact Limited Use disclosure:

```text
Email Radar's use and transfer to any other app of information received from Google APIs will adhere to Google API Services User Data Policy, including the Limited Use requirements.
```

- The app provides visible data controls:
  - disconnect local session,
  - link to revoke access in Google Account permissions,
  - in-app OAuth token revocation attempt,
  - in-app active local data deletion,
  - mailto path for formal deletion/privacy requests and backup handling.
- Production config must set `GOOGLE_TOKEN_ENCRYPTION_KEY` so Google OAuth
  access and refresh tokens are encrypted at rest.
- Production config must keep `ALLOW_ACCOUNT_HEADER_AUTH=false`; account access
  should be resolved from the post-OAuth Django session.
- Production config should keep `GMAIL_BODY_CHAR_LIMIT` set to a finite value,
  currently `6000`, unless there is a documented reason to process more text.

## Google Cloud Console values

Create or use a production-only Google Cloud project. Do not reuse development,
testing, staging, or localhost OAuth clients for verification.

Recommended project name:

```text
Email Radar Production
```

Enable APIs:

```text
Gmail API
```

Generate the backend token encryption key before deployment:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Branding / OAuth consent screen:

```text
App name: Email Radar
User support email: suporte@email-radar.com
App homepage: https://email-radar.com/
Privacy policy: https://email-radar.com/privacy
Terms of service: https://email-radar.com/terms
Authorized domain: email-radar.com
Developer contact email: suporte@email-radar.com
Audience: External
Publishing status: Production when ready to submit
```

Logo:

```text
Square PNG/JPG/BMP, ideally 120x120, under 1 MB.
Must represent Email Radar.
Must not include Google, Gmail, or modified Google product marks.
```

OAuth web client:

```text
Application type: Web application
Name: Email Radar Web Production
Authorized JavaScript origin: https://email-radar.com
Authorized redirect URI: https://email-radar.com/api/auth/google/callback/
```

Remove these from the production project before verification:

```text
localhost URLs
127.0.0.1 URLs
staging domains
mailguard.example.com
unused redirect URIs
unused OAuth clients
```

Data Access:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Scope justification:

```text
Email Radar uses https://www.googleapis.com/auth/gmail.readonly to read Gmail messages, headers, labels, snippets, sender information, links, attachment metadata, and body text needed to provide user-facing email security analysis. The app identifies phishing, spam, scams, spoofing, suspicious links, suspicious attachment metadata, and related risks, then displays a risk score and explanation to the user. Narrower scopes such as gmail.metadata are insufficient because Email Radar must inspect message body text and contextual content to detect and explain phishing and scam patterns. Broader scopes such as gmail.modify and https://mail.google.com/ are not requested because Email Radar does not send, edit, move, or delete email.
```

## Domain verification

Use the same Google account that is an Owner or Editor on the Google Cloud
project.

1. Open Google Search Console.
2. Add property.
3. Choose Domain property, not URL-prefix.
4. Enter:

```text
email-radar.com
```

5. Copy the TXT verification record.
6. Add the TXT record at the DNS provider.
7. Wait for DNS propagation.
8. Click Verify.
9. Keep the TXT record permanently.
10. Confirm Search Console shows the root domain as verified before submitting
    OAuth verification.

## Demo video storyboard

Record the same production app you submit for verification. Add English voice
narration or on-screen captions. Upload as an unlisted YouTube video or another
Google-accessible link.

### Scene 1: App identity

Show:

- `https://email-radar.com/` in the address bar.
- Email Radar branding.
- Homepage description.
- Privacy Policy and Terms links.

Suggested narration:

```text
This is Email Radar at email-radar.com. Email Radar helps users analyze Gmail messages for phishing, spam, scams, spoofing, suspicious links, suspicious attachment metadata, and related email security risks.
```

### Scene 2: Privacy policy and Limited Use

Open `https://email-radar.com/privacy`.

Show the exact Limited Use disclosure.

Suggested narration:

```text
The privacy policy explains what Gmail data is accessed, how it is used, how it is stored, who it may be shared with, retention and deletion, AI processing, and Google API Limited Use compliance.
```

### Scene 3: Pre-OAuth disclosure

Return to the homepage.

Show the disclosure immediately above the Google button and the required
checkbox.

Suggested narration:

```text
Before OAuth begins, Email Radar explains that it requests Gmail read-only access, lists the data categories processed, explains that the data is used only for email security analysis, and states that Email Radar cannot send, edit, move, or delete email.
```

### Scene 4: OAuth flow

Check the consent checkbox and click `Continuar com Google`.

On the Google consent screen:

- Ensure the language selector shows English.
- Show the full consent screen.
- Show app name: `Email Radar`.
- Show the requested Gmail read-only scope.
- Show the browser URL containing the OAuth `client_id`.
- Do not show client secret, server secrets, environment variables, or private
  credentials.

Suggested narration:

```text
This is the OAuth consent screen for Email Radar. The app name is shown correctly, and the requested scope is Gmail read-only. The browser address bar shows the OAuth client ID used by this production web client.
```

### Scene 5: Data use inside the app

Approve OAuth using a test Gmail account.

Show:

- Redirect back to Email Radar.
- Inbox or spam sync.
- Message list.
- A message detail or preview.
- Analysis result: risk score, classification, explanation, security signals.

Suggested narration:

```text
Email Radar uses the Gmail read-only data to show messages in the security analysis interface and generate a risk score, classification, and explanation for the user. This is the user-facing feature enabled by the Gmail scope.
```

### Scene 6: Read-only behavior

Show that the app does not provide Gmail write actions.

Suggested narration:

```text
Email Radar does not provide send, edit, move, or delete actions for Gmail. The requested access is read-only and is used only for this security analysis workflow.
```

### Scene 7: User controls

Open profile/settings.

Show:

- disconnect local session,
- link to Google permissions,
- deletion request link.

Suggested narration:

```text
Users can disconnect the local Email Radar session, revoke OAuth access in their Google Account permissions, and request deletion of Email Radar data.
```

## CASA and security assessment preparation

Because Email Radar stores Gmail-derived records and OAuth tokens in the backend
and can transmit Gmail-derived excerpts to an AI provider, plan for restricted
scope security review and CASA.

Google's current review email requires CASA Tier 2 by August 14, 2026. Complete
Tier 2 with TAC Security or another CASA authorized assessor, or voluntarily
complete Tier 3 if you want a broader lab-validated assessment. Keep the final
assessment validation letter and any remediation evidence ready for Google.

Prepare these artifacts:

- Architecture diagram.
- Data-flow diagram from Google OAuth to Gmail API, backend, database, AI
  provider, frontend, logs, and backups.
- List of subprocessors and what data each receives.
- Data retention and deletion procedure.
- Incident response plan.
- Access control policy.
- Vulnerability management policy.
- Dependency scanning evidence.
- Secret scanning evidence.
- SAST/DAST results.
- Backup encryption and retention evidence.
- Token encryption and key management evidence.
- Production IAM/administrator list with MFA.
- Logging and monitoring plan.

Engineering posture in this repository:

- Google access and refresh tokens are encrypted at rest when
  `GOOGLE_TOKEN_ENCRYPTION_KEY` is configured.
- Production can disable account selection by `X-Mailguard-Account`; after OAuth,
  the backend resolves the connected Google account from the Django session.
- Profile controls support local session disconnect, OAuth token revocation
  attempt, active local data deletion, Google Account permissions revocation,
  and support email for formal deletion/privacy requests.
- Real first-party user authentication is still recommended before a broad
  multi-user public launch, especially if the closed beta Basic Auth layer is
  removed.
- Ensure AI provider terms prohibit training general models on Gmail-derived
  data.
- Document and enforce retention periods for Gmail body text, headers, analysis
  outputs, logs, and backups.

## Submission sequence

1. Deploy the updated homepage, privacy policy, terms, and profile controls.
2. Verify `email-radar.com` as a Search Console Domain property using the Google
   Cloud project Owner/Editor account.
3. Confirm the production OAuth client has no localhost/staging URLs.
4. Confirm the app requests only `gmail.readonly`.
5. Publish or verify branding.
6. Record the demo video against production.
7. Go to Verification Center.
8. Submit data access verification with the scope justification and video link.
9. Monitor the support email and developer contact emails daily.
10. Respond to Google review questions with exact screenshots/video references.
11. Complete CASA Tier 2 by August 14, 2026 and provide the assessor validation
    letter when requested.

## Reply template for Google's email

```text
Hello Google Third Party Data Safety Team,

Thank you for the update. We have reviewed the restricted-scope OAuth
verification requirements for project 561450909122
(custom-search-api-455516) and have updated Email Radar's implementation and
verification materials accordingly.

We understand that CASA Tier 2 is required by August 14, 2026. We are starting
the CASA assessment process with an authorized CASA assessor and will provide
the required validation evidence when available.

The application currently requests only the Gmail readonly restricted scope:
https://www.googleapis.com/auth/gmail.readonly

We have also confirmed the app homepage, privacy policy, terms, in-product
OAuth disclosure, minimum-scope justification, AI/ML training disclosure, and
user data controls are aligned with the Google API Services User Data Policy,
Google Workspace API User Data and Developer Policy, and Limited Use
requirements.

Please continue the verification process and let us know if you need any
additional materials while the CASA process is underway.
```
