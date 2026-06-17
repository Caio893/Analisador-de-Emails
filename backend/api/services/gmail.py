import base64
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from email.utils import parseaddr
from urllib.parse import urlencode, unquote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from typing import Iterable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from api.models import EmailAnalysis, EmailRecord, GoogleAccount
from api.services.analysis_queue import enqueue_email_analysis
from api.services.openai_analysis import analysis_content_hash, analyze_email_locally

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
FOLDER_LABELS = {
    EmailRecord.Folder.INBOX: "INBOX",
    EmailRecord.Folder.SPAM: "SPAM",
}
LABEL_FOLDERS = {label: folder for folder, label in FOLDER_LABELS.items()}
GMAIL_LIST_FIELDS = "messages(id,threadId),nextPageToken,resultSizeEstimate"
GMAIL_MESSAGE_FIELDS = (
    "id,threadId,historyId,labelIds,snippet,internalDate,sizeEstimate,payload"
)
GMAIL_HISTORY_FIELDS = (
    "history(id,messagesAdded(message(id,threadId,labelIds)),"
    "messagesDeleted(message(id,threadId,labelIds)),"
    "labelsAdded(message(id,threadId,labelIds),labelIds),"
    "labelsRemoved(message(id,threadId,labelIds),labelIds)),"
    "historyId,nextPageToken"
)
GMAIL_DISPLAY_FIELDS = "id,payload"
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


class GmailHistoryLimitExceeded(Exception):
    pass


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
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    from googleapiclient.discovery import build

    http = httplib2.Http(timeout=settings.GOOGLE_API_TIMEOUT_SECONDS)
    authed_http = AuthorizedHttp(credentials, http=http)
    return build("gmail", "v1", http=authed_http, cache_discovery=False)


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
        .get(userId="me", id=gmail_id, format="full", fields=GMAIL_DISPLAY_FIELDS)
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
        "gmail_history_id": str(message.get("historyId", "")),
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


def list_message_refs(
    service,
    folder: str,
    max_results: int,
    *,
    query: str = "",
) -> list[dict]:
    label = FOLDER_LABELS[folder]
    refs: list[dict] = []
    page_token = None

    while len(refs) < max_results:
        remaining = max_results - len(refs)
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=[label],
                maxResults=min(remaining, 500),
                pageToken=page_token,
                q=query or None,
                includeSpamTrash=folder == EmailRecord.Folder.SPAM,
                fields=GMAIL_LIST_FIELDS,
            )
            .execute()
        )
        refs.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return refs[:max_results]


def get_message(service, gmail_id: str) -> dict:
    return (
        service.users()
        .messages()
        .get(userId="me", id=gmail_id, format="full", fields=GMAIL_MESSAGE_FIELDS)
        .execute()
    )


def batch_get_messages(service, gmail_ids: list[str], batch_size: int = 50) -> list[dict]:
    if not gmail_ids:
        return []

    if not hasattr(service, "new_batch_http_request"):
        return [get_message(service, gmail_id) for gmail_id in gmail_ids]

    messages_by_id: dict[str, dict] = {}

    for start in range(0, len(gmail_ids), batch_size):
        chunk = gmail_ids[start : start + batch_size]

        def callback(request_id, response, exception):
            if exception:
                return
            messages_by_id[str(request_id)] = response

        batch = service.new_batch_http_request(callback=callback)
        for gmail_id in chunk:
            request = (
                service.users()
                .messages()
                .get(userId="me", id=gmail_id, format="full", fields=GMAIL_MESSAGE_FIELDS)
            )
            batch.add(request, request_id=gmail_id)
        batch.execute()

    return [messages_by_id[gmail_id] for gmail_id in gmail_ids if gmail_id in messages_by_id]


def iter_messages(service, folder: str, max_results: int) -> Iterable[dict]:
    refs = list_message_refs(service, folder, max_results, query=settings.GMAIL_SYNC_QUERY)
    ids = [item["id"] for item in refs]
    yield from batch_get_messages(service, ids)


def folder_from_labels(label_ids: Iterable[str], default: str | None = None) -> str | None:
    labels = set(label_ids or [])
    if FOLDER_LABELS[EmailRecord.Folder.SPAM] in labels:
        return EmailRecord.Folder.SPAM
    if FOLDER_LABELS[EmailRecord.Folder.INBOX] in labels:
        return EmailRecord.Folder.INBOX
    return default if default in FOLDER_LABELS else None


def current_mailbox_history_id(service) -> str:
    try:
        profile = service.users().getProfile(userId="me", fields="historyId").execute()
    except TypeError:
        profile = service.users().getProfile(userId="me").execute()
    return str(profile.get("historyId", ""))


def parse_watch_expiration(value: str | int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return None


def refresh_gmail_watch(account: GoogleAccount, service) -> bool:
    if not settings.GMAIL_WATCH_TOPIC:
        return False

    renew_after = timezone.now() + timedelta(hours=settings.GMAIL_WATCH_RENEWAL_HOURS)
    if account.gmail_watch_expiration and account.gmail_watch_expiration > renew_after:
        return False

    response = (
        service.users()
        .watch(
            userId="me",
            body={
                "topicName": settings.GMAIL_WATCH_TOPIC,
                "labelIds": list(FOLDER_LABELS.values()),
                "labelFilterBehavior": "INCLUDE",
            },
            fields="historyId,expiration",
        )
        .execute()
    )
    account.gmail_history_id = str(response.get("historyId") or account.gmail_history_id or "")
    account.gmail_watch_expiration = parse_watch_expiration(response.get("expiration"))
    account.save(update_fields=["gmail_history_id", "gmail_watch_expiration", "updated_at"])
    return True


def history_message_ids(
    service,
    start_history_id: str,
    folders: Iterable[str],
    *,
    max_changes: int | None = None,
) -> tuple[list[str], str]:
    ids: list[str] = []
    seen: set[str] = set()
    page_token = None
    latest_history_id = start_history_id
    change_limit = settings.GMAIL_HISTORY_MAX_CHANGES if max_changes is None else max_changes

    while True:
        response = (
            service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
                maxResults=500,
                pageToken=page_token,
                fields=GMAIL_HISTORY_FIELDS,
            )
            .execute()
        )
        latest_history_id = str(response.get("historyId") or latest_history_id or "")
        for history in response.get("history", []):
            latest_history_id = str(history.get("id") or latest_history_id)
            for bucket in ("messagesAdded", "messagesDeleted", "labelsAdded", "labelsRemoved"):
                for entry in history.get(bucket, []) or []:
                    message = entry.get("message") or {}
                    gmail_id = message.get("id")
                    if not gmail_id or gmail_id in seen:
                        continue
                    seen.add(gmail_id)
                    ids.append(gmail_id)
                    if change_limit > 0 and len(ids) >= change_limit:
                        raise GmailHistoryLimitExceeded(
                            f"Gmail history exceeded {change_limit} changed messages."
                        )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return ids, latest_history_id


def delete_local_message(account: GoogleAccount, gmail_id: str, folders: Iterable[str]) -> int:
    queryset = EmailRecord.objects.filter(
        account=account,
        gmail_id=gmail_id,
        folder__in=tuple(folders),
    )
    count = queryset.count()
    queryset.delete()
    return count


def delete_stale_folder_messages(account: GoogleAccount, folder: str, current_gmail_ids: set[str]) -> int:
    queryset = EmailRecord.objects.filter(account=account, folder=folder)
    if current_gmail_ids:
        queryset = queryset.exclude(gmail_id__in=current_gmail_ids)
    count = queryset.count()
    queryset.delete()
    return count


def sync_account_emails(
    account: GoogleAccount,
    folders: Iterable[str] = (EmailRecord.Folder.INBOX, EmailRecord.Folder.SPAM),
    max_results: int | None = None,
) -> dict[str, int]:
    service = build_gmail_service(account)
    limit = max_results or settings.GMAIL_SYNC_MAX_RESULTS
    folders = tuple(folder for folder in folders if folder in FOLDER_LABELS)
    synced = 0
    local_analyzed = 0
    queued = 0
    removed = 0

    def persist_message(message: dict, folder: str) -> tuple[bool, bool, bool]:
        parsed = parse_gmail_message(message, folder)
        email, created = EmailRecord.objects.update_or_create(
            account=account,
            gmail_id=parsed["gmail_id"],
            defaults=parsed,
        )
        content_hash = analysis_content_hash(email)
        if email.content_hash != content_hash:
            email.content_hash = content_hash
            email.save(update_fields=["content_hash", "updated_at"])

        did_local = False
        did_queue = False
        if not email.hidden_at:
            analysis = getattr(email, "analysis", None)
            status = getattr(analysis, "status", "")
            if created or not analysis:
                analyze_email_locally(email)
                did_local = True
            elif (
                analysis.model == "local-heuristic"
                and analysis.content_hash
                and analysis.content_hash != content_hash
                and status not in {EmailAnalysis.Status.QUEUED, EmailAnalysis.Status.RUNNING}
            ):
                analyze_email_locally(email, force=True)
                did_local = True

            if settings.ANALYSIS_QUEUE_AUTO_ENQUEUE:
                email = EmailRecord.objects.select_related("analysis").get(pk=email.pk)
                did_queue = enqueue_email_analysis(email)

        return created, did_local, did_queue

    def reconcile_folder(folder: str, *, fetch_all: bool = False) -> tuple[int, int, int, int]:
        refs = list_message_refs(service, folder, limit, query=settings.GMAIL_SYNC_QUERY)
        current_gmail_ids = [item["id"] for item in refs if item.get("id")]
        current_gmail_id_set = set(current_gmail_ids)
        ids_to_fetch = current_gmail_ids

        if not fetch_all:
            existing_ids = set(
                EmailRecord.objects.filter(
                    account=account,
                    folder=folder,
                    gmail_id__in=current_gmail_ids,
                ).values_list("gmail_id", flat=True)
            )
            ids_to_fetch = [gmail_id for gmail_id in current_gmail_ids if gmail_id not in existing_ids]

        folder_synced = 0
        folder_local_analyzed = 0
        folder_queued = 0
        if ids_to_fetch:
            for message in batch_get_messages(service, ids_to_fetch):
                _, did_local, did_queue = persist_message(message, folder)
                folder_synced += 1
                folder_local_analyzed += int(did_local)
                folder_queued += int(did_queue)

        folder_removed = delete_stale_folder_messages(account, folder, current_gmail_id_set)
        return folder_synced, folder_local_analyzed, folder_queued, folder_removed

    reconciled_folders: set[str] = set()

    try:
        if account.gmail_history_id:
            ids, latest_history_id = history_message_ids(service, account.gmail_history_id, folders)
            if ids:
                messages_by_id = {message["id"]: message for message in batch_get_messages(service, ids)}
                for gmail_id in ids:
                    message = messages_by_id.get(gmail_id)
                    if not message:
                        removed += delete_local_message(account, gmail_id, folders)
                        continue

                    folder = folder_from_labels(message.get("labelIds") or [])
                    if folder and folder in folders:
                        _, did_local, did_queue = persist_message(message, folder)
                        synced += 1
                        local_analyzed += int(did_local)
                        queued += int(did_queue)
                    else:
                        removed += delete_local_message(account, gmail_id, folders)
            if latest_history_id:
                account.gmail_history_id = latest_history_id
        else:
            raise ValueError("No Gmail history checkpoint available.")
    except Exception as exc:
        if exc.__class__.__name__ != "HttpError" or getattr(getattr(exc, "resp", None), "status", None) == 404:
            account.gmail_history_id = ""
        for folder in folders:
            folder_synced, folder_local_analyzed, folder_queued, folder_removed = reconcile_folder(
                folder,
                fetch_all=True,
            )
            synced += folder_synced
            local_analyzed += folder_local_analyzed
            queued += folder_queued
            removed += folder_removed
            reconciled_folders.add(folder)
        try:
            account.gmail_history_id = current_mailbox_history_id(service) or account.gmail_history_id
        except Exception:
            pass

    for folder in folders:
        if folder in reconciled_folders:
            continue
        try:
            folder_synced, folder_local_analyzed, folder_queued, folder_removed = reconcile_folder(folder)
        except Exception:
            continue
        synced += folder_synced
        local_analyzed += folder_local_analyzed
        queued += folder_queued
        removed += folder_removed

    try:
        refresh_gmail_watch(account, service)
    except Exception:
        pass

    account.last_synced_at = timezone.now()
    account.save(update_fields=["last_synced_at", "gmail_history_id", "updated_at"])
    return {
        "synced": synced,
        "analyzed": 0,
        "localAnalyzed": local_analyzed,
        "queued": queued,
        "removed": removed,
    }
