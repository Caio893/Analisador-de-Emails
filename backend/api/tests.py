import base64
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import EmailAnalysis, EmailRecord, GoogleAccount, TrustedSenderRule
from api.services.gmail import (
    EmailDisplayContent,
    GMAIL_READONLY_SCOPE,
    build_google_auth_url,
    extract_display_content_from_payload,
    parse_gmail_message,
    sync_account_emails,
)
from api.services.openai_analysis import (
    OPENAI_SYSTEM_PROMPT,
    analyze_email,
    build_openai_analysis_payload,
    create_response_with_retry,
    normalize_payload,
    readable_text_for_ai,
)


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def encoded_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class GoogleAuthTests(TestCase):
    @override_settings(
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/api/auth/google/callback/",
    )
    def test_auth_url_uses_readonly_scope(self):
        class FakeFlow:
            scopes = []
            redirect_uri = ""
            code_verifier = "verifier-123"

            @classmethod
            def from_client_config(cls, _config, scopes, state=None, redirect_uri=None, **_kwargs):
                cls.scopes = scopes
                cls.redirect_uri = redirect_uri
                return cls()

            def authorization_url(self, **_kwargs):
                return "https://accounts.google.com/o/oauth2/auth", "state-123"

        with patch("api.services.gmail.oauth_flow_class", return_value=FakeFlow):
            authorization_url, state, code_verifier = build_google_auth_url()

        self.assertIn("accounts.google.com", authorization_url)
        self.assertEqual(FakeFlow.scopes, [GMAIL_READONLY_SCOPE])
        self.assertEqual(FakeFlow.redirect_uri, "http://localhost:8000/api/auth/google/callback/")
        self.assertEqual(state, "state-123")
        self.assertEqual(code_verifier, "verifier-123")

    def test_auth_start_redirects_to_google(self):
        client = APIClient()
        with patch(
            "api.views.build_google_auth_url",
            return_value=("https://accounts.google.com/o/oauth2/auth", "abc", "verifier-123"),
        ):
            response = client.get("/api/auth/google/start/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://accounts.google.com/o/oauth2/auth")
        self.assertEqual(client.session["google_oauth_code_verifier"], "verifier-123")

    def test_auth_callback_redirect_does_not_expose_google_tokens(self):
        client = APIClient()
        session = client.session
        session["google_oauth_state"] = "state-123"
        session["google_oauth_code_verifier"] = "verifier-123"
        session.save()

        account = GoogleAccount(email="owner@example.com")
        with patch("api.views.exchange_callback_for_account", return_value=account):
            response = client.get("/api/auth/google/callback/?state=state-123&code=code-123")

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertIn("/app/inbox", location)
        self.assertIn("connected=1", location)
        self.assertIn("account=owner%40example.com", location)
        self.assertNotIn("code-123", location)
        self.assertNotIn("access_token", location)
        self.assertNotIn("refresh_token", location)
        self.assertEqual(client.session["google_account_email"], "owner@example.com")


class GoogleTokenEncryptionTests(TestCase):
    @override_settings(
        GOOGLE_TOKEN_ENCRYPTION_KEY="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        GOOGLE_TOKEN_ENCRYPTION_FALLBACK_KEYS=[],
    )
    def test_google_oauth_tokens_are_encrypted_at_rest(self):
        account = GoogleAccount.objects.create(
            email="encrypted@example.com",
            access_token="access-token",
            refresh_token="refresh-token",
            scopes=[GMAIL_READONLY_SCOPE],
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "select access_token, refresh_token from api_googleaccount where id = %s",
                [account.pk],
            )
            raw_access_token, raw_refresh_token = cursor.fetchone()

        self.assertTrue(raw_access_token.startswith("fernet:"))
        self.assertTrue(raw_refresh_token.startswith("fernet:"))
        self.assertNotIn("access-token", raw_access_token)
        self.assertNotIn("refresh-token", raw_refresh_token)

        account.refresh_from_db()
        self.assertEqual(account.access_token, "access-token")
        self.assertEqual(account.refresh_token, "refresh-token")


class GmailParsingTests(TestCase):
    def test_parse_gmail_message_extracts_headers_and_plain_body(self):
        message = {
            "id": "gmail-1",
            "threadId": "thread-1",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Reset your password",
            "internalDate": "1700000000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Security Team <security@example.com>"},
                    {"name": "Subject", "value": "Password reset"},
                ],
                "mimeType": "text/plain",
                "body": {"data": encoded("Click here to reset your password.")},
            },
        }

        parsed = parse_gmail_message(message, EmailRecord.Folder.INBOX)

        self.assertEqual(parsed["gmail_id"], "gmail-1")
        self.assertEqual(parsed["from_email"], "security@example.com")
        self.assertEqual(parsed["subject"], "Password reset")
        self.assertIn("reset your password", parsed["body"])
        self.assertTrue(parsed["unread"])
        self.assertFalse(parsed["has_attachments"])
        self.assertEqual(parsed["attachment_count"], 0)
        self.assertEqual(parsed["metadata"]["sender_domain"], "example.com")

    def test_parse_gmail_message_extracts_attachment_metadata_without_default_body_cap(self):
        message = {
            "id": "gmail-2",
            "threadId": "thread-2",
            "labelIds": ["SPAM"],
            "snippet": "Invoice attached",
            "internalDate": "1700000000000",
            "sizeEstimate": 2048,
            "payload": {
                "headers": [
                    {"name": "From", "value": "Billing <billing@example.net>"},
                    {"name": "Subject", "value": "Invoice"},
                    {"name": "Authentication-Results", "value": "spf=fail"},
                ],
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": encoded("Open http://bad.example/login " + ("x" * 6000))},
                    },
                    {
                        "filename": "invoice.exe",
                        "mimeType": "application/octet-stream",
                        "body": {"attachmentId": "att-1", "size": 1234},
                    },
                ],
            },
        }

        with override_settings(GMAIL_BODY_CHAR_LIMIT=0):
            parsed = parse_gmail_message(message, EmailRecord.Folder.SPAM)

        self.assertEqual(len(parsed["body"]), len("Open http://bad.example/login " + ("x" * 6000)))
        self.assertTrue(parsed["has_attachments"])
        self.assertEqual(parsed["attachment_count"], 1)
        self.assertEqual(parsed["metadata"]["link_domains"], ["bad.example"])
        self.assertEqual(parsed["metadata"]["dangerous_attachment_extensions"], [".exe"])

    def test_display_content_preserves_html_and_embeds_inline_images(self):
        payload = {
            "mimeType": "multipart/related",
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": encoded(
                            '<p>Hello <a href="https://example.com">open</a>'
                            '<img src="cid:logo@example"></p>'
                        )
                    },
                },
                {
                    "mimeType": "image/png",
                    "headers": [{"name": "Content-ID", "value": "<logo@example>"}],
                    "body": {"data": encoded_bytes(b"png-bytes")},
                },
            ],
        }

        display = extract_display_content_from_payload(payload)

        self.assertEqual(display.source, "gmail-html")
        self.assertIn('<a href="https://example.com">open</a>', display.html)
        self.assertIn('src="data:image/png;base64,cG5nLWJ5dGVz"', display.html)
        self.assertNotIn("cid:logo@example", display.html)


class GmailSyncTests(TestCase):
    def setUp(self):
        self.account = GoogleAccount.objects.create(
            email="owner@example.com",
            access_token="token",
            refresh_token="refresh",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_ANALYSIS_ENABLED=True)
    def test_sync_uses_local_analysis_without_calling_openai(self):
        message = {
            "id": "gmail-sync-local",
            "threadId": "thread-sync-local",
            "labelIds": ["INBOX"],
            "snippet": "Weekly update",
            "internalDate": "1700000000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "Subject", "value": "Weekly update"},
                ],
                "mimeType": "text/plain",
                "body": {"data": encoded("No action required.")},
            },
        }

        with (
            patch("api.services.gmail.build_gmail_service", return_value=object()),
            patch("api.services.gmail.iter_messages", return_value=[message]),
            patch("api.services.openai_analysis.create_response_with_retry") as openai_call,
        ):
            result = sync_account_emails(self.account, folders=[EmailRecord.Folder.INBOX])

        self.assertEqual(result["synced"], 1)
        self.assertEqual(result["analyzed"], 0)
        self.assertEqual(result["localAnalyzed"], 1)
        openai_call.assert_not_called()

        email = EmailRecord.objects.select_related("analysis").get(gmail_id="gmail-sync-local")
        self.assertEqual(email.analysis.model, "local-heuristic")


class OpenAIAnalysisTests(TestCase):
    def setUp(self):
        self.account = GoogleAccount.objects.create(
            email="security@example.com",
            access_token="token",
            refresh_token="refresh",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        self.email = EmailRecord.objects.create(
            account=self.account,
            gmail_id="gmail-openai-test",
            folder=EmailRecord.Folder.INBOX,
            from_name="Security Team",
            from_email="security@example.com",
            subject="Weekly security update",
            snippet="No action required.",
            body="Routine account security summary.",
            received_at=timezone.now(),
        )

    def test_normalize_payload_clamps_score_and_preserves_schema_fields(self):
        result = normalize_payload(
            {
                "classification": "dangerous",
                "risk_score": 999,
                "threat_categories": ["phishing", "malware"],
                "reason": "Credential theft attempt.",
                "signals": ["urgent", "fake domain"],
            },
            "gpt-test",
        )

        self.assertEqual(result.classification, "dangerous")
        self.assertEqual(result.risk_score, 100)
        self.assertEqual(result.threat_categories, ["phishing", "malware"])
        self.assertEqual(result.signals, ["urgent", "fake domain"])
        self.assertEqual(result.model, "gpt-test")

    @override_settings(GMAIL_BODY_CHAR_LIMIT=0)
    def test_openai_payload_is_minimal_and_sends_full_stored_body_when_unlimited(self):
        self.email.metadata = {
            "sender_domain": "example.com",
            "links": ["https://example.com/reset"],
            "authentication_results": "spf=pass",
        }
        self.email.body = "abcdefghijklmnop"

        payload = build_openai_analysis_payload(self.email)

        self.assertEqual(set(payload.keys()), {"folder", "subject", "sender", "domain", "body"})
        self.assertEqual(payload["subject"], "Weekly security update")
        self.assertEqual(payload["sender"], {"name": "Security Team", "email": "security@example.com"})
        self.assertEqual(payload["domain"], "example.com")
        self.assertEqual(payload["body"], "abcdefghijklmnop")
        self.assertNotIn("metadata", payload)
        self.assertNotIn("gmail_id", payload)

    @override_settings(GMAIL_BODY_CHAR_LIMIT=0)
    def test_openai_payload_removes_raw_urls_from_body(self):
        self.email.body = (
            "Seu design esta pronto.\n"
            "https://l.engage.canva.com/ss/c/u001.Note3it1gaozj0PIggVG9tplar3juom3GwdJknmjC20uH_3_AhWFYsSBnxWrxljf/4qm/i40QMX47TZKlAMw-anHEJw/t1/h001.eRCPqbD0J6eztJjGxalWc_bd6FjbR6L9Qq8jNeYddOo\n"
            "Obrigado por usar o Canva."
        )

        payload = build_openai_analysis_payload(self.email)

        self.assertEqual(payload["body"], "Seu design esta pronto.\nObrigado por usar o Canva.")
        self.assertNotIn("https://", payload["body"])
        self.assertNotIn("l.engage.canva.com", payload["body"])

    def test_readable_text_for_ai_removes_plain_urls_but_keeps_text(self):
        text = readable_text_for_ai(
            "Confira o alerta https://tracking.example.com/pixel?id=123 e responda ao suporte."
        )

        self.assertEqual(text, "Confira o alerta e responda ao suporte.")

    def test_openai_system_prompt_requires_brazilian_portuguese(self):
        prompt = OPENAI_SYSTEM_PROMPT.lower()

        self.assertIn("portugues brasileiro", prompt)
        self.assertIn("nao responda em ingles", prompt)

    def test_analyze_email_reuses_cached_analysis(self):
        cached = EmailAnalysis.objects.create(
            email=self.email,
            risk="trusted",
            risk_score=5,
            reason="Already analyzed.",
            model="gpt-test",
        )

        with patch("api.services.openai_analysis.analyze_with_openai") as advanced_analysis:
            analysis = analyze_email(self.email)

        self.assertEqual(analysis.pk, cached.pk)
        advanced_analysis.assert_not_called()

    @override_settings(OPENAI_RETRY_ATTEMPTS=1, OPENAI_RETRY_BASE_SECONDS=0)
    def test_openai_retry_system_retries_transient_errors(self):
        class RateLimitError(Exception):
            pass

        expected_response = object()

        class FakeResponses:
            def __init__(self):
                self.calls = 0

            def create(self, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise RateLimitError("temporary rate limit")
                return expected_response

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponses()

        client = FakeClient()
        with patch("api.services.openai_analysis.time.sleep") as sleep:
            response = create_response_with_retry(client, model="gpt-test", input_messages=[])

        self.assertIs(response, expected_response)
        self.assertEqual(client.responses.calls, 2)
        sleep.assert_called_once_with(0)

    def test_failed_openai_analysis_falls_back_to_local_heuristic(self):
        with patch("api.services.openai_analysis.analyze_with_openai", side_effect=Exception("service down")):
            analysis = analyze_email(self.email)

        self.assertEqual(analysis.model, "local-heuristic")
        self.assertIn(analysis.risk, {"trusted", "slightly_trusted", "suspicious", "dangerous"})

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_ANALYSIS_ENABLED=True)
    def test_trusted_sender_rule_skips_openai(self):
        TrustedSenderRule.objects.create(
            account=self.account,
            rule_type=TrustedSenderRule.RuleType.EMAIL,
            value=self.email.from_email,
        )

        with patch("api.services.openai_analysis.create_response_with_retry") as openai_call:
            analysis = analyze_email(self.email)

        openai_call.assert_not_called()
        self.assertEqual(analysis.risk, "trusted")
        self.assertEqual(analysis.risk_score, 3)
        self.assertEqual(analysis.model, "trusted-sender-rule")

    @override_settings(OPENAI_ANALYSIS_ENABLED=False)
    def test_trusted_domain_rule_does_not_bypass_gmail_spam_signal(self):
        spam_email = EmailRecord.objects.create(
            account=self.account,
            gmail_id="gmail-spam-trusted-domain",
            folder=EmailRecord.Folder.SPAM,
            from_name="Trusted Billing",
            from_email="billing@example.com",
            subject="Invoice",
            snippet="Please review invoice.",
            body="Please review the invoice.",
            metadata={"sender_domain": "example.com"},
            received_at=timezone.now(),
        )
        TrustedSenderRule.objects.create(
            account=self.account,
            rule_type=TrustedSenderRule.RuleType.DOMAIN,
            value="example.com",
        )

        analysis = analyze_email(spam_email)

        self.assertEqual(analysis.model, "local-heuristic")
        self.assertEqual(analysis.risk, "dangerous")

    def test_trusted_sender_api_creates_rule_and_updates_current_email(self):
        client = APIClient()
        EmailAnalysis.objects.create(
            email=self.email,
            risk="suspicious",
            risk_score=62,
            reason="Initial suspicious classification.",
            model="gpt-test",
        )
        response = client.post(
            "/api/trusted-senders/",
            {"emailId": str(self.email.pk), "ruleType": "domain"},
            format="json",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["applied"])
        self.assertEqual(payload["rule"]["ruleType"], "domain")
        self.assertEqual(payload["rule"]["value"], "example.com")
        self.assertEqual(payload["email"]["risk"], "trusted")
        self.assertEqual(payload["email"]["riskScore"], 3)


class BetaBasicAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(
        BETA_BASIC_AUTH_ENABLED=True,
        BETA_BASIC_AUTH_USERNAME="beta",
        BETA_BASIC_AUTH_PASSWORD="secret",
        BETA_BASIC_AUTH_REALM="MailGuard Closed Beta",
        BETA_BASIC_AUTH_EXEMPT_PATHS=["/api/healthz/"],
    )
    def test_beta_basic_auth_blocks_unauthorized_requests(self):
        response = self.client.get("/api/summary/")

        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response["WWW-Authenticate"])

    @override_settings(
        BETA_BASIC_AUTH_ENABLED=True,
        BETA_BASIC_AUTH_USERNAME="beta",
        BETA_BASIC_AUTH_PASSWORD="secret",
        BETA_BASIC_AUTH_EXEMPT_PATHS=["/api/healthz/"],
    )
    def test_beta_basic_auth_allows_authorized_requests(self):
        credentials = base64.b64encode(b"beta:secret").decode("ascii")
        response = self.client.get("/api/summary/", HTTP_AUTHORIZATION=f"Basic {credentials}")

        self.assertEqual(response.status_code, 200)

    @override_settings(
        BETA_BASIC_AUTH_ENABLED=True,
        BETA_BASIC_AUTH_USERNAME="beta",
        BETA_BASIC_AUTH_PASSWORD="secret",
        BETA_BASIC_AUTH_EXEMPT_PATHS=["/api/healthz/"],
    )
    def test_health_endpoint_is_exempt_from_beta_basic_auth(self):
        response = self.client.get("/api/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class EmailApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = GoogleAccount.objects.create(
            email="owner@example.com",
            access_token="token",
            refresh_token="refresh",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        self.safe_email = EmailRecord.objects.create(
            account=self.account,
            gmail_id="gmail-safe",
            folder=EmailRecord.Folder.INBOX,
            from_name="Alice",
            from_email="alice@example.com",
            subject="Weekly notes",
            snippet="Safe update",
            body="Project notes",
            received_at=timezone.now(),
        )
        self.risky_email = EmailRecord.objects.create(
            account=self.account,
            gmail_id="gmail-risky",
            folder=EmailRecord.Folder.SPAM,
            from_name="Bank Alert",
            from_email="alert@example.net",
            subject="Urgent account verification",
            snippet="Verify now",
            body="Click to verify your password",
            received_at=timezone.now(),
        )
        EmailAnalysis.objects.create(
            email=self.safe_email,
            risk="trusted",
            risk_score=4,
            reason="No suspicious indicators.",
        )
        EmailAnalysis.objects.create(
            email=self.risky_email,
            risk="dangerous",
            risk_score=92,
            reason="Urgency and credential theft pattern.",
        )

    def test_email_list_paginates_and_searches(self):
        response = self.client.get(
            "/api/emails/?folder=spam&search=verification",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["risk"], "dangerous")
        self.assertEqual(payload["items"][0]["riskScore"], 92)

    def test_email_detail_adds_display_body_without_changing_stored_ai_body(self):
        with patch(
            "api.views.fetch_email_display_content",
            return_value=EmailDisplayContent(
                html='<p>Full <a href="https://example.com">HTML</a></p>',
                text="Full HTML",
                source="gmail-html",
            ),
        ):
            response = self.client.get(
                f"/api/emails/{self.safe_email.pk}/",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["body"], "Project notes")
        self.assertEqual(
            payload["displayBodyHtml"],
            '<p>Full <a href="https://example.com">HTML</a></p>',
        )
        self.assertEqual(payload["displayBodyText"], "Full HTML")
        self.assertEqual(payload["displayBodySource"], "gmail-html")
        self.assertEqual(build_openai_analysis_payload(self.safe_email)["body"], "Project notes")

    def test_summary_counts_cached_analysis(self):
        response = self.client.get("/api/summary/", HTTP_X_MAILGUARD_ACCOUNT=self.account.email)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "analyzedToday": 2,
                "spamDetected": 1,
                "suspicious": 0,
                "riskRate": 50,
            },
        )

    def test_remove_email_hides_it_from_lists_detail_and_summary(self):
        response = self.client.post(
            f"/api/emails/{self.risky_email.pk}/remove/",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"removed": True, "id": str(self.risky_email.pk)})

        self.risky_email.refresh_from_db()
        self.assertIsNotNone(self.risky_email.hidden_at)

        list_response = self.client.get(
            "/api/emails/?folder=spam",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["total"], 0)

        detail_response = self.client.get(
            f"/api/emails/{self.risky_email.pk}/",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )
        self.assertEqual(detail_response.status_code, 404)

        summary_response = self.client.get("/api/summary/", HTTP_X_MAILGUARD_ACCOUNT=self.account.email)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["analyzedToday"], 1)
        self.assertEqual(summary_response.json()["spamDetected"], 0)
        self.assertEqual(summary_response.json()["riskRate"], 0)

    def test_sync_endpoint_uses_account_header(self):
        with patch("api.views.sync_account_emails", return_value={"synced": 2, "analyzed": 1}):
            response = self.client.post(
                "/api/emails/sync/",
                {"folders": ["inbox"]},
                format="json",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account"], self.account.email)
        self.assertEqual(response.json()["synced"], 2)

    @override_settings(ALLOW_ACCOUNT_HEADER_AUTH=False)
    def test_api_uses_session_account_when_header_fallback_is_disabled(self):
        other = GoogleAccount.objects.create(
            email="other@example.com",
            access_token="token",
            refresh_token="refresh",
            scopes=[GMAIL_READONLY_SCOPE],
        )
        session = self.client.session
        session["google_account_email"] = self.account.email
        session.save()

        response = self.client.get(
            "/api/summary/",
            HTTP_X_MAILGUARD_ACCOUNT=other.email,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzedToday"], 2)

    @override_settings(ALLOW_ACCOUNT_HEADER_AUTH=False)
    def test_api_rejects_header_only_account_selection_in_production_mode(self):
        response = self.client.get(
            "/api/summary/",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "analyzedToday": 0,
                "spamDetected": 0,
                "suspicious": 0,
                "riskRate": 0,
            },
        )

    def test_delete_account_removes_local_google_data(self):
        response = self.client.delete(
            "/api/account/",
            HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted": True, "account": self.account.email})
        self.assertFalse(GoogleAccount.objects.filter(pk=self.account.pk).exists())
        self.assertFalse(EmailRecord.objects.filter(account_id=self.account.pk).exists())

    def test_revoke_account_calls_google_revocation_endpoint(self):
        with patch("api.views.revoke_google_token", return_value=True) as revoke:
            response = self.client.post(
                "/api/account/revoke/",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"revoked": True, "account": self.account.email})
        revoke.assert_called_once()

    def test_analyze_endpoint_analyzes_only_local_requested_folder_emails(self):
        self.safe_email.analysis.model = "local-heuristic"
        self.safe_email.analysis.save(update_fields=["model"])

        def fake_analyze(email, *, force=False, bulk=True):
            self.assertTrue(force)
            self.assertTrue(bulk)
            analysis, _ = EmailAnalysis.objects.update_or_create(
                email=email,
                defaults={
                    "risk": "trusted",
                    "risk_score": 5,
                    "reason": "AI reviewed.",
                    "model": "gpt-test",
                },
            )
            return analysis

        with patch("api.views.analyze_email", side_effect=fake_analyze) as analyze:
            response = self.client.post(
                "/api/emails/analyze/",
                {"folder": "inbox"},
                format="json",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["folder"], "inbox")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["eligible"], 1)
        self.assertEqual(payload["skippedAlreadyAnalyzed"], 0)
        self.assertEqual(payload["aiAnalyzed"], 1)
        analyze.assert_called_once()
        self.assertEqual(analyze.call_args.args[0].pk, self.safe_email.pk)

    def test_analyze_endpoint_skips_already_ai_analyzed_emails(self):
        self.safe_email.analysis.model = "gpt-test"
        self.safe_email.analysis.save(update_fields=["model"])

        with patch("api.views.analyze_email") as analyze:
            response = self.client.post(
                "/api/emails/analyze/",
                {"folder": "inbox"},
                format="json",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["eligible"], 0)
        self.assertEqual(payload["skippedAlreadyAnalyzed"], 1)
        self.assertEqual(payload["analyzed"], 0)
        analyze.assert_not_called()

    def test_analyze_endpoint_uses_local_fallback_instead_of_500_for_email_errors(self):
        self.safe_email.analysis.model = "local-heuristic"
        self.safe_email.analysis.save(update_fields=["model"])

        with patch("api.views.analyze_email", side_effect=Exception("openai request failed")):
            response = self.client.post(
                "/api/emails/analyze/",
                {"folder": "inbox"},
                format="json",
                HTTP_X_MAILGUARD_ACCOUNT=self.account.email,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["eligible"], 1)
        self.assertEqual(payload["skippedAlreadyAnalyzed"], 0)
        self.assertEqual(payload["analyzed"], 1)
        self.assertEqual(payload["aiAnalyzed"], 0)
        self.assertEqual(payload["localFallback"], 1)
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["errors"][0]["emailId"], str(self.safe_email.pk))
