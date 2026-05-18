import base64
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from email.utils import parseaddr
from urllib.parse import urlencode, unquote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from typing import Iterable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from api.models import EmailRecord, GoogleAccount
from api.services.openai_analysis import analyze_email_locally

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
FOLDER_LABELS = {
    EmailRecord.Folder.INBOX: "INBOX",
    EmailRecord.Folder.SPAM: "SPAM",
}
URL_RE = re.compile(r"https?://[^\s<>\")']+", re.IGNORECASE)
DANGEROUS_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".exe",
    ".hta",
    ".js",
    ".jse",
    ".msi",
    ".scr",
    ".vbe",
    ".vbs",
    ".wsf",
}


@dataclass(frozen=True)
class EmailDisplayContent:
    html: str = ""
    text: str = ""
    source: str = "gmail"


def oauth_flow_class():
    from google_auth_oauthlib.flow import Flow

    return Flow


def allow_local_oauth_transport() -> None:
    if settings.OAUTHLIB_INSECURE_TRANSPORT:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def google_client_config() -> dict[str, dict[str, str]]:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ImproperlyConfigured("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured.")

    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }


def build_google_auth_url(state: str | None = None) -> tuple[str, str, str]:
    allow_local_oauth_transport()
    flow = oauth_flow_class().from_client_config(
        google_client_config(),
        scopes=[GMAIL_READONLY_SCOPE],
        state=state,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    )
    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url, returned_state, getattr(flow, "code_verifier", "")


def exchange_callback_for_account(
    authorization_response: str,
    state: str | None = None,
    code_verifier: str | None = None,
) -> GoogleAccount:
    allow_local_oauth_transport()
    flow = oauth_flow_class().from_client_config(
        google_client_config(),
        scopes=[GMAIL_READONLY_SCOPE],
        state=state,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
        code_verifier=code_verifier,
    )
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    service = build_gmail_service_from_credentials(credentials)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]

    existing = GoogleAccount.objects.filter(email=email).first()
    refresh_token = credentials.refresh_token or (existing.refresh_token if existing else "")
    account, _ = GoogleAccount.objects.update_or_create(
        email=email,
        defaults={
            "access_token": credentials.token,
            "refresh_token": refresh_token,
            "token_uri": credentials.token_uri,
            "scopes": list(credentials.scopes or [GMAIL_READONLY_SCOPE]),
            "token_expiry": credentials.expiry,
        },
    )
    return account


def credentials_for_account(account: GoogleAccount):
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token or None,
        token_uri=account.token_uri,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=account.scopes or [GMAIL_READONLY_SCOPE],
    )


def build_gmail_service_from_credentials(credentials):
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def build_gmail_service(account: GoogleAccount):
    from google.auth.transport.requests import Request

    credentials = credentials_for_account(account)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        account.access_token = credentials.token
        account.token_expiry = credentials.expiry
        if credentials.refresh_token:
            account.refresh_token = credentials.refresh_token
        account.save(update_fields=["access_token", "refresh_token", "token_expiry", "updated_at"])
    return build_gmail_service_from_credentials(credentials)


def revoke_google_token(account: GoogleAccount) -> bool:
    token = account.refresh_token or account.access_token
    if not token:
        return False

    data = urlencode({"token": token}).encode("utf-8")
    request = UrlRequest(
        "https://oauth2.googleapis.com/revoke",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except HTTPError as exc:
        return exc.code in {400, 401}
    except URLError:
        return False


def decode_base64url_bytes(value: str) -> bytes:
    if not value:
        return b""
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def decode_base64url(value: str) -> str:
    return decode_base64url_bytes(value).decode("utf-8", errors="replace")


def data_url_from_base64url(value: str, mime_type: str) -> str:
    try:
        encoded = base64.b64encode(decode_base64url_bytes(value)).decode("ascii")
    except Exception:
        return ""
    return f"data:{mime_type or 'application/octet-stream'};base64,{encoded}"


def strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_tags).strip()


def limit_text(value: str, limit: int) -> str:
    if limit <= 0:
        return value
    return value[:limit]


def collect_payload_metadata(payload: dict) -> dict:
    metadata = {
        "attachment_count": 0,
        "attachment_filenames": [],
        "attachment_mime_types": [],
        "dangerous_attachment_extensions": [],
        "has_html": False,
    }

    def walk(part: dict) -> None:
        filename = part.get("filename") or ""
        mime_type = part.get("mimeType") or ""
        body = part.get("body") or {}

        if mime_type == "text/html":
            metadata["has_html"] = True

        if filename or body.get("attachmentId"):
            metadata["attachment_count"] += 1
            if filename:
                metadata["attachment_filenames"].append(filename)
                extension = os.path.splitext(filename.lower())[1]
                if extension in DANGEROUS_EXTENSIONS:
                    metadata["dangerous_attachment_extensions"].append(extension)
            if mime_type:
                metadata["attachment_mime_types"].append(mime_type)

        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})
    metadata["attachment_filenames"] = metadata["attachment_filenames"][:10]
    metadata["attachment_mime_types"] = sorted(set(metadata["attachment_mime_types"]))[:10]
    metadata["dangerous_attachment_extensions"] = sorted(
        set(metadata["dangerous_attachment_extensions"])
    )
    return metadata


def extract_body(payload: dict) -> str:
    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    def walk(part: dict) -> None:
        if part.get("filename"):
            return

        body = part.get("body") or {}
        if body.get("attachmentId"):
            return

        data = body.get("data")
        mime_type = part.get("mimeType", "")
        if data and mime_type == "text/plain":
            plain_chunks.append(decode_base64url(data))
        elif data and mime_type == "text/html":
            html_chunks.append(strip_html(decode_base64url(data)))

        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})
    body = "\n\n".join(chunk.strip() for chunk in plain_chunks if chunk.strip())
    if not body:
        body = "\n\n".join(chunk.strip() for chunk in html_chunks if chunk.strip())
    return limit_text(body, settings.GMAIL_BODY_CHAR_LIMIT)


def extract_urls(text: str) -> list[str]:
    urls = [match.rstrip(".,;:!?]") for match in URL_RE.findall(text or "")]
    return list(dict.fromkeys(urls))[:20]


def extract_domains(urls: Iterable[str]) -> list[str]:
    domains = []
    for url in urls:
        parsed = urlparse(url)
        if parsed.hostname:
            domains.append(parsed.hostname.lower())
    return sorted(set(domains))[:20]


def header_map(payload: dict) -> dict[str, str]:
    headers = payload.get("headers") or []
    return {header.get("name", "").lower(): header.get("value", "") for header in headers}


def normalize_content_id(value: str) -> str:
    content_id = unquote((value or "").strip())
    if content_id.lower().startswith("cid:"):
        content_id = content_id[4:]
    return content_id.strip("<>").strip().lower()


def replace_inline_image_references(html: str, inline_images: dict[str, str]) -> str:
    if not html or not inline_images:
        return html

    def replace(match: re.Match[str]) -> str:
        content_id = normalize_content_id(match.group(1))
        return inline_images.get(content_id, match.group(0))

    return re.sub(r"cid:([^'\"\s>)]+)", replace, html, flags=re.IGNORECASE)


def extract_display_content_from_payload(
    payload: dict,
    *,
    service=None,
    message_id: str = "",
) -> EmailDisplayContent:
    html_chunks: list[str] = []
    plain_chunks: list[str] = []
    inline_images: dict[str, str] = {}

    def attachment_data(attachment_id: str) -> str:
        if not service or not message_id or not attachment_id:
            return ""
        try:
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        except Exception:
            return ""
        return attachment.get("data", "")

    def walk(part: dict) -> None:
        headers = header_map(part)
        body = part.get("body") or {}
        mime_type = (part.get("mimeType") or "").split(";", 1)[0].lower()
        disposition = headers.get("content-disposition", "").lower()
        filename = part.get("filename") or ""
        data = body.get("data", "")
        attachment_id = body.get("attachmentId", "")
        content_id = normalize_content_id(headers.get("content-id", ""))

        if content_id and mime_type.startswith("image/"):
            image_data = data or attachment_data(attachment_id)
            data_url = data_url_from_base64url(image_data, mime_type) if image_data else ""
            if data_url:
                inline_images[content_id] = data_url

        is_attachment = disposition.startswith("attachment") or (
            bool(filename) and not disposition.startswith("inline")
        )
        if data and not attachment_id and not is_attachment:
            if mime_type == "text/html":
                html_chunks.append(decode_base64url(data))
            elif mime_type == "text/plain":
                plain_chunks.append(decode_base64url(data))

        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})

    html_body = replace_inline_image_references(
        "\n".join(chunk.strip() for chunk in html_chunks if chunk.strip()),
        inline_images,
    )
    text_body = "\n\n".join(chunk.strip() for chunk in plain_chunks if chunk.strip())
    source = "gmail-html" if html_body else "gmail-text" if text_body else "gmail"
    return EmailDisplayContent(html=html_body, text=text_body, source=source)


def fetch_email_display_content(account: GoogleAccount, gmail_id: str) -> EmailDisplayContent:
    service = build_gmail_service(account)
    message = (
        service.users()
        .messages()
        .get(userId="me", id=gmail_id, format="full")
        .execute()
    )
    return extract_display_content_from_payload(
        message.get("payload") or {},
        service=service,
        message_id=gmail_id,
    )


def received_datetime(message: dict) -> datetime:
    internal_date = message.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=dt_timezone.utc)
    return timezone.now()


def parse_gmail_message(message: dict, folder: str) -> dict:
    payload = message.get("payload") or {}
    headers = header_map(payload)
    from_name, from_email = parseaddr(headers.get("from", ""))
    body = extract_body(payload)
    payload_metadata = collect_payload_metadata(payload)
    urls = extract_urls(f"{message.get('snippet', '')}\n{body}")
    sender_domain = from_email.split("@")[-1].lower() if "@" in from_email else ""
    metadata = {
        "sender_domain": sender_domain,
        "reply_to": headers.get("reply-to", ""),
        "return_path": headers.get("return-path", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "date": headers.get("date", ""),
        "message_id": headers.get("message-id", ""),
        "labels": message.get("labelIds") or [],
        "size_estimate": message.get("sizeEstimate"),
        "body_char_count": len(body),
        "link_count": len(urls),
        "links": urls,
        "link_domains": extract_domains(urls),
        "authentication_results": headers.get("authentication-results", ""),
        "spf_result": headers.get("received-spf", ""),
        **payload_metadata,
    }

    return {
        "gmail_id": message["id"],
        "thread_id": message.get("threadId", ""),
        "folder": folder,
        "from_name": from_name or from_email,
        "from_email": from_email,
        "subject": headers.get("subject", ""),
        "snippet": message.get("snippet", ""),
        "body": body,
        "has_attachments": payload_metadata["attachment_count"] > 0,
        "attachment_count": payload_metadata["attachment_count"],
        "metadata": metadata,
        "received_at": received_datetime(message),
        "unread": "UNREAD" in (message.get("labelIds") or []),
        "raw_headers": headers,
    }


def iter_messages(service, folder: str, max_results: int) -> Iterable[dict]:
    label = FOLDER_LABELS[folder]
    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=[label],
            maxResults=max_results,
            includeSpamTrash=folder == EmailRecord.Folder.SPAM,
        )
        .execute()
    )
    for item in response.get("messages", []):
        yield (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )


def sync_account_emails(
    account: GoogleAccount,
    folders: Iterable[str] = (EmailRecord.Folder.INBOX, EmailRecord.Folder.SPAM),
    max_results: int | None = None,
) -> dict[str, int]:
    service = build_gmail_service(account)
    limit = max_results or settings.GMAIL_SYNC_MAX_RESULTS
    synced = 0
    local_analyzed = 0

    for folder in folders:
        if folder not in FOLDER_LABELS:
            continue

        for message in iter_messages(service, folder, limit):
            parsed = parse_gmail_message(message, folder)
            email, created = EmailRecord.objects.update_or_create(
                account=account,
                gmail_id=parsed["gmail_id"],
                defaults=parsed,
            )
            synced += 1
            if email.hidden_at:
                continue
            if created or not hasattr(email, "analysis"):
                analyze_email_locally(email)
                local_analyzed += 1

    account.last_synced_at = timezone.now()
    account.save(update_fields=["last_synced_at", "updated_at"])
    return {"synced": synced, "analyzed": 0, "localAnalyzed": local_analyzed, "queued": 0}
