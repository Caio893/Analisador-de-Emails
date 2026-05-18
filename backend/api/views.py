import logging
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailRecord, GoogleAccount, TrustedSenderRule
from .serializers import EmailRecordSerializer
from .services.gmail import (
    EmailDisplayContent,
    build_google_auth_url,
    exchange_callback_for_account,
    fetch_email_display_content,
    revoke_google_token,
    sync_account_emails,
)
from .services.openai_analysis import analyze_email, analyze_email_locally
from .services.trusted_senders import create_trusted_sender_rule, trusted_sender_rule_for_email

logger = logging.getLogger(__name__)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


def frontend_redirect(**params: str) -> HttpResponseRedirect:
    query = urlencode({key: value for key, value in params.items() if value})
    target = f"{settings.FRONTEND_URL.rstrip('/')}/app/inbox"
    if query:
        target = f"{target}?{query}"
    return HttpResponseRedirect(target)


def account_from_request(request) -> GoogleAccount | None:
    session_email = request.session.get("google_account_email")
    if session_email:
        return GoogleAccount.objects.filter(email=session_email).first()

    if not settings.ALLOW_ACCOUNT_HEADER_AUTH:
        return None

    email = request.headers.get("X-Mailguard-Account") or request.query_params.get("account")
    if email:
        return GoogleAccount.objects.filter(email=email).first()
    return GoogleAccount.objects.order_by("-updated_at").first()


def int_query_param(request, name: str, default: int, minimum: int, maximum: int | None = None) -> int:
    try:
        value = int(request.query_params.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


class GoogleAuthStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        authorization_url, state, code_verifier = build_google_auth_url()
        request.session["google_oauth_state"] = state
        request.session["google_oauth_code_verifier"] = code_verifier
        return HttpResponseRedirect(authorization_url)


class GoogleAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        expected_state = request.session.get("google_oauth_state")
        returned_state = request.query_params.get("state")
        if expected_state and returned_state != expected_state:
            return HttpResponseBadRequest("Invalid Google OAuth state.")

        code_verifier = request.session.get("google_oauth_code_verifier")
        account = exchange_callback_for_account(
            request.build_absolute_uri(),
            returned_state,
            code_verifier=code_verifier,
        )
        request.session.pop("google_oauth_state", None)
        request.session.pop("google_oauth_code_verifier", None)
        request.session["google_account_email"] = account.email
        return frontend_redirect(account=account.email, connected="1")


class GoogleAccountView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before deleting local data."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        account_email = account.email
        account.delete()
        if request.session.get("google_account_email") == account_email:
            request.session.pop("google_account_email", None)
        return Response({"deleted": True, "account": account_email})


class GoogleAccountRevokeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before revoking OAuth access."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        revoked = revoke_google_token(account)
        return Response({"revoked": revoked, "account": account.email})


class EmailSyncView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before syncing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        requested_folders = request.data.get("folders") or [
            EmailRecord.Folder.INBOX,
            EmailRecord.Folder.SPAM,
        ]
        if isinstance(requested_folders, str):
            requested_folders = [requested_folders]

        result = sync_account_emails(account, folders=requested_folders)
        return Response({"account": account.email, **result})


class EmailAnalyzeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before analyzing emails."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        folder = request.data.get("folder", EmailRecord.Folder.INBOX)
        if folder not in {EmailRecord.Folder.INBOX, EmailRecord.Folder.SPAM}:
            return Response({"detail": "folder must be inbox or spam."}, status=status.HTTP_400_BAD_REQUEST)

        folder_queryset = (
            EmailRecord.objects.select_related("analysis")
            .filter(account=account, folder=folder, hidden_at__isnull=True)
            .order_by("-received_at")
        )
        queryset = folder_queryset.filter(Q(analysis__isnull=True) | Q(analysis__model="local-heuristic"))

        total = folder_queryset.count()
        eligible = queryset.count()
        skipped_already_analyzed = total - eligible
        ai_analyzed = 0
        local_fallback = 0
        trusted = 0
        failed = 0
        errors = []

        for email in queryset.iterator():
            try:
                analysis = analyze_email(email, force=True, bulk=True)
            except Exception as exc:
                logger.exception("Failed to analyze email %s", email.pk)
                try:
                    analysis = analyze_email_locally(email, force=True)
                    local_fallback += 1
                    errors.append({"emailId": str(email.pk), "detail": str(exc)})
                    continue
                except Exception as fallback_exc:
                    logger.exception("Failed to apply local fallback to email %s", email.pk)
                    failed += 1
                    errors.append({"emailId": str(email.pk), "detail": str(fallback_exc)})
                    continue
            if analysis.model == "local-heuristic":
                local_fallback += 1
            elif analysis.model == "trusted-sender-rule":
                trusted += 1
            else:
                ai_analyzed += 1

        return Response(
            {
                "account": account.email,
                "folder": folder,
                "total": total,
                "eligible": eligible,
                "skippedAlreadyAnalyzed": skipped_already_analyzed,
                "analyzed": ai_analyzed + local_fallback + trusted,
                "aiAnalyzed": ai_analyzed,
                "localFallback": local_fallback,
                "trusted": trusted,
                "failed": failed,
                "errors": errors[:5],
            }
        )


class EmailListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before viewing emails."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        folder = request.query_params.get("folder", EmailRecord.Folder.INBOX)
        if folder not in {EmailRecord.Folder.INBOX, EmailRecord.Folder.SPAM}:
            return Response({"detail": "folder must be inbox or spam."}, status=status.HTTP_400_BAD_REQUEST)

        page = int_query_param(request, "page", default=1, minimum=1)
        page_size = int_query_param(request, "page_size", default=10, minimum=1, maximum=100)
        search = request.query_params.get("search", "").strip()

        queryset = EmailRecord.objects.select_related("analysis").filter(
            account=account,
            folder=folder,
            hidden_at__isnull=True,
        )
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search)
                | Q(from_name__icontains=search)
                | Q(from_email__icontains=search)
                | Q(snippet__icontains=search)
                | Q(body__icontains=search)
            )

        total = queryset.count()
        start = (page - 1) * page_size
        items = queryset[start : start + page_size]
        return Response(
            {
                "items": EmailRecordSerializer(items, many=True).data,
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": start + page_size < total,
            }
        )


class EmailDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk: int):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before viewing emails."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = get_object_or_404(
            EmailRecord.objects.select_related("analysis"),
            pk=pk,
            account=account,
            hidden_at__isnull=True,
        )
        display_content = EmailDisplayContent(text=email.body, source="stored")
        try:
            fetched_content = fetch_email_display_content(email.account, email.gmail_id)
            if fetched_content.html or fetched_content.text:
                display_content = fetched_content
        except Exception:
            logger.warning("Failed to fetch display content for email %s", email.pk, exc_info=True)

        data = EmailRecordSerializer(email).data
        data["displayBodyHtml"] = display_content.html
        data["displayBodyText"] = display_content.text or email.body
        data["displayBodySource"] = display_content.source
        return Response(data)


class EmailRemoveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before removing emails."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = get_object_or_404(EmailRecord, pk=pk, account=account, hidden_at__isnull=True)
        email.hidden_at = timezone.now()
        email.save(update_fields=["hidden_at", "updated_at"])
        return Response({"removed": True, "id": str(email.pk)})


class TrustedSenderRuleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {"detail": "Connect a Gmail account before trusting senders."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email_id = request.data.get("emailId")
        rule_type = request.data.get("ruleType")
        if rule_type not in {TrustedSenderRule.RuleType.EMAIL, TrustedSenderRule.RuleType.DOMAIN}:
            return Response(
                {"detail": "ruleType must be email or domain."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = get_object_or_404(
            EmailRecord.objects.select_related("account", "analysis"),
            pk=email_id,
            account=account,
        )

        try:
            rule, created = create_trusted_sender_rule(email, rule_type)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        applied = trusted_sender_rule_for_email(email) is not None
        if applied:
            analyze_email(email, force=True)
            email = EmailRecord.objects.select_related("account", "analysis").get(pk=email.pk)

        return Response(
            {
                "rule": {"ruleType": rule.rule_type, "value": rule.value, "created": created},
                "applied": applied,
                "detail": None
                if applied
                else "Rule saved, but this message still requires analysis because it is in Spam or has a dangerous attachment signal.",
                "email": EmailRecordSerializer(email).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        account = account_from_request(request)
        if not account:
            return Response(
                {
                    "analyzedToday": 0,
                    "spamDetected": 0,
                    "suspicious": 0,
                    "riskRate": 0,
                }
            )

        emails = EmailRecord.objects.filter(account=account, hidden_at__isnull=True)
        total = emails.count()
        risky = emails.filter(analysis__risk_score__gte=50).count()
        today = timezone.now().date()

        return Response(
            {
                "analyzedToday": emails.filter(analysis__analyzed_at__date=today).count(),
                "spamDetected": emails.filter(folder=EmailRecord.Folder.SPAM).count(),
                "suspicious": emails.filter(analysis__risk="suspicious").count(),
                "riskRate": round((risky / max(total, 1)) * 100),
            }
        )
