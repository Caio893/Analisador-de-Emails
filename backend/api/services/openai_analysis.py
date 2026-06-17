import hashlib
import json
import random
import re
import time
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from api.models import EmailAnalysis, EmailRecord
from api.services.trusted_senders import trusted_sender_rule_for_email

CLASSIFICATIONS = {"trusted", "slightly_trusted", "suspicious", "dangerous"}
LOCAL_MODELS = {"local-heuristic", "trusted-sender-rule"}

OPENAI_SYSTEM_PROMPT = (
    "Analise o JSON de um email para seguranca. Responda apenas pelo schema. "
    "Classifique como trusted, slightly_trusted, suspicious ou dangerous. "
    "Use portugues brasileiro em reason e signals; nao responda em ingles. "
    "Considere spam, phishing, "
    "malware, virus, spoofing, dominio do remetente, dominios de links, anexos, "
    "SPF/DKIM/DMARC quando presentes e consistencia com o corpo legivel. "
    "Nao invente risco de anexo sem metadados. O campo body nao contem URLs brutas."
)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {
            "type": "string",
            "enum": ["trusted", "slightly_trusted", "suspicious", "dangerous"],
        },
        "risk_score": {"type": "integer"},
        "threat_categories": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["spam", "phishing", "malware", "virus", "spoofing", "scam", "none"],
            },
        },
        "reason": {"type": "string"},
        "signals": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["classification", "risk_score", "threat_categories", "reason", "signals"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class AnalysisResult:
    classification: str
    risk_score: int
    threat_categories: list[str]
    reason: str
    signals: list[str]
    model: str


def clamp_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def limit_text(value: str, limit: int) -> str:
    if limit <= 0:
        return value
    return value[:limit]


def readable_text_for_ai(value: str) -> str:
    without_urls = re.sub(r"https?://\S+", " ", value or "", flags=re.IGNORECASE)
    without_angle_urls = re.sub(r"<\s*>", " ", without_urls)
    collapsed_spaces = re.sub(r"[ \t\r\f\v]+", " ", without_angle_urls)
    lines = [line.strip() for line in collapsed_spaces.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def compact_header(value: object, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def build_analysis_payload(email: EmailRecord) -> dict[str, object]:
    metadata = email.metadata or {}
    compact_metadata = {
        "sender_domain": metadata.get("sender_domain", ""),
        "reply_to": metadata.get("reply_to", ""),
        "return_path": metadata.get("return_path", ""),
        "to": metadata.get("to", ""),
        "cc": metadata.get("cc", ""),
        "date": metadata.get("date", ""),
        "message_id": metadata.get("message_id", ""),
        "labels": metadata.get("labels", []),
        "size_estimate": metadata.get("size_estimate"),
        "has_html": metadata.get("has_html", False),
        "link_count": metadata.get("link_count", 0),
        "links": metadata.get("links", [])[:10],
        "link_domains": metadata.get("link_domains", [])[:10],
        "attachment_filenames": metadata.get("attachment_filenames", [])[:10],
        "attachment_mime_types": metadata.get("attachment_mime_types", [])[:10],
        "dangerous_attachment_extensions": metadata.get("dangerous_attachment_extensions", []),
        "authentication_results": str(metadata.get("authentication_results", ""))[:1000],
        "spf_result": str(metadata.get("spf_result", ""))[:500],
    }

    return {
        "gmail_id": email.gmail_id,
        "folder": email.folder,
        "sender": {
            "name": email.from_name,
            "email": email.from_email,
            "domain": compact_metadata["sender_domain"],
        },
        "subject": email.subject,
        "snippet": email.snippet,
        "body_text": limit_text(email.body, settings.GMAIL_BODY_CHAR_LIMIT),
        "has_attachments": email.has_attachments,
        "attachment_count": email.attachment_count,
        "metadata": compact_metadata,
    }


def sender_domain_for_email(email: EmailRecord) -> str:
    metadata = email.metadata or {}
    domain = str(metadata.get("sender_domain") or "").strip().lower()
    if domain:
        return domain
    if "@" in email.from_email:
        return email.from_email.rsplit("@", 1)[-1].strip().lower()
    return ""


def build_openai_analysis_payload(email: EmailRecord) -> dict[str, object]:
    metadata = email.metadata or {}
    domain = sender_domain_for_email(email)
    readable_body = readable_text_for_ai(email.body)
    return {
        "folder": email.folder,
        "subject": email.subject[:300],
        "sender": {
            "name": email.from_name,
            "email": email.from_email,
        },
        "domain": domain,
        "links": {
            "count": metadata.get("link_count", 0),
            "domains": (metadata.get("link_domains") or [])[:8],
        },
        "attachments": {
            "count": email.attachment_count,
            "filenames": (metadata.get("attachment_filenames") or [])[:6],
            "mime_types": (metadata.get("attachment_mime_types") or [])[:6],
            "dangerous_extensions": metadata.get("dangerous_attachment_extensions", []),
        },
        "auth": {
            "spf": compact_header(metadata.get("spf_result"), 300),
            "authentication_results": compact_header(metadata.get("authentication_results"), 500),
        },
        "body": limit_text(readable_body, settings.OPENAI_BODY_CHAR_LIMIT),
    }


def analysis_content_hash(email: EmailRecord) -> str:
    payload = build_openai_analysis_payload(email)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def heuristic_analysis(email: EmailRecord, reason_prefix: str = "") -> AnalysisResult:
    metadata = email.metadata or {}
    text = json.dumps(build_analysis_payload(email), ensure_ascii=False).lower()
    signals: list[str] = []
    categories: set[str] = set()

    suspicious_terms = [
        "password",
        "senha",
        "urgent",
        "urgente",
        "verify",
        "verificar",
        "account suspended",
        "conta bloqueada",
        "pix",
        "invoice",
        "fatura",
        "click",
        "clique",
        "login",
    ]
    malware_terms = ["virus", "malware", "trojan", "ransomware", "macro", "payload"]

    for term in suspicious_terms:
        if term in text:
            signals.append(term)

    for term in malware_terms:
        if term in text:
            signals.append(term)
            categories.add("malware" if term != "virus" else "virus")

    if email.folder == EmailRecord.Folder.SPAM:
        signals.append("gmail_spam_label")
        categories.add("spam")

    if metadata.get("dangerous_attachment_extensions"):
        signals.append("dangerous_attachment_extension")
        categories.add("malware")

    if len(signals) >= 4 or "gmail_spam_label" in signals:
        classification = "dangerous"
        score = 88
        categories.add("phishing")
    elif len(signals) >= 2 or email.has_attachments:
        classification = "suspicious"
        score = 62
        if len(signals) >= 2:
            categories.add("phishing")
    elif signals:
        classification = "slightly_trusted"
        score = 32
    else:
        classification = "trusted"
        score = 8

    reason = "Classificacao preliminar aplicada por regras locais."
    if reason_prefix:
        reason = f"{reason_prefix} {reason}"
    if signals:
        reason = f"{reason} Sinais observados: {', '.join(signals[:8])}."

    return AnalysisResult(
        classification=classification,
        risk_score=score,
        threat_categories=sorted(categories) or ["none"],
        reason=reason,
        signals=signals[:8],
        model="local-heuristic",
    )


def trusted_sender_analysis(email: EmailRecord) -> AnalysisResult | None:
    rule = trusted_sender_rule_for_email(email)
    if not rule:
        return None

    label = "remetente" if rule.rule_type == "email" else "dominio"
    return AnalysisResult(
        classification="trusted",
        risk_score=3,
        threat_categories=["none"],
        reason=f"Classificado como confiavel por regra de {label}: {rule.value}. Analise avancada ignorada para economizar tokens.",
        signals=[f"trusted_{rule.rule_type}:{rule.value}"],
        model="trusted-sender-rule",
    )


def parse_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text

    output = getattr(response, "output", None)
    if not output:
        return ""

    chunks: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", "")
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def normalize_payload(payload: dict[str, object], model: str) -> AnalysisResult:
    signals = payload.get("signals", [])
    if not isinstance(signals, list):
        signals = []

    threat_categories = payload.get("threat_categories", [])
    if not isinstance(threat_categories, list):
        threat_categories = []

    classification = payload.get("classification")
    if classification not in CLASSIFICATIONS:
        classification = "suspicious"

    reason = payload.get("reason")
    return AnalysisResult(
        classification=str(classification),
        risk_score=clamp_score(payload.get("risk_score")),
        threat_categories=[str(category) for category in threat_categories] or ["none"],
        reason=str(reason or "Nenhuma explicacao retornada."),
        signals=[str(signal) for signal in signals],
        model=model,
    )


def retryable_openai_error(exc: Exception) -> bool:
    retryable_names = {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
    }
    if exc.__class__.__name__ in retryable_names:
        return True
    return getattr(exc, "status_code", None) in {429, 500, 502, 503, 504}


def create_response_with_retry(client, *, model: str, input_messages: list[dict[str, str]]):
    attempts = max(1, settings.OPENAI_RETRY_ATTEMPTS + 1)
    base_delay = max(0.0, settings.OPENAI_RETRY_BASE_SECONDS)

    for attempt in range(attempts):
        try:
            return client.responses.create(
                model=model,
                input=input_messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "email_security_analysis",
                        "strict": True,
                        "schema": ANALYSIS_SCHEMA,
                    }
                },
                max_output_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
            )
        except Exception as exc:
            if attempt >= attempts - 1 or not retryable_openai_error(exc):
                raise
            delay = base_delay * (2**attempt)
            if delay:
                delay *= 1 + random.random()
            time.sleep(delay)


def friendly_openai_failure(exc: Exception) -> str:
    if exc.__class__.__name__ == "RateLimitError":
        return "A analise avancada atingiu um limite temporario."
    return "A analise avancada nao pode ser concluida agora."


def advanced_analysis_count_today(account) -> int:
    today = timezone.now().date()
    return EmailAnalysis.objects.filter(
        email__account=account,
        analyzed_at__date=today,
    ).exclude(model__in=LOCAL_MODELS).count()


def daily_analysis_limit_reached(email: EmailRecord) -> bool:
    limit = settings.OPENAI_DAILY_ANALYSIS_LIMIT
    return limit > 0 and advanced_analysis_count_today(email.account) >= limit


def reusable_analysis_for_hash(
    email: EmailRecord,
    *,
    model: str,
    content_hash: str,
) -> EmailAnalysis | None:
    if not content_hash:
        return None

    prompt_version = settings.OPENAI_PROMPT_VERSION
    current = getattr(email, "analysis", None)
    if (
        current
        and current.status == EmailAnalysis.Status.COMPLETED
        and current.model == model
        and current.content_hash == content_hash
        and current.prompt_version == prompt_version
    ):
        return current

    return (
        EmailAnalysis.objects.select_related("email")
        .filter(
            email__account=email.account,
            content_hash=content_hash,
            prompt_version=prompt_version,
            status=EmailAnalysis.Status.COMPLETED,
        )
        .exclude(Q(model__in=LOCAL_MODELS) | Q(email=email))
        .first()
    )


def analyze_with_openai(email: EmailRecord, *, bulk: bool = True) -> AnalysisResult:
    trusted_result = trusted_sender_analysis(email)
    if trusted_result:
        return trusted_result

    if not settings.OPENAI_ANALYSIS_ENABLED:
        return heuristic_analysis(email, "A analise avancada esta desativada.")

    if not settings.OPENAI_API_KEY:
        return heuristic_analysis(email, "A chave da OpenAI nao esta configurada.")

    if daily_analysis_limit_reached(email):
        return heuristic_analysis(email, "O limite diario de analises avancadas foi atingido.")

    from openai import OpenAI

    payload = build_openai_analysis_payload(email)
    model = settings.OPENAI_BULK_MODEL if bulk else settings.OPENAI_MODEL
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT_SECONDS)
    response = create_response_with_retry(
        client,
        model=model,
        input_messages=[
            {
                "role": "system",
                "content": OPENAI_SYSTEM_PROMPT,
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    text = parse_response_text(response)
    if not text:
        return heuristic_analysis(email, "A analise avancada retornou uma resposta vazia.")

    match = re.search(r"\{.*\}", text, re.DOTALL)
    payload = json.loads(match.group(0) if match else text)
    return normalize_payload(payload, model)


def save_analysis_result(email: EmailRecord, result: AnalysisResult) -> EmailAnalysis:
    content_hash = analysis_content_hash(email)
    status = (
        EmailAnalysis.Status.LOCAL
        if result.model in LOCAL_MODELS
        else EmailAnalysis.Status.COMPLETED
    )
    analysis, _ = EmailAnalysis.objects.update_or_create(
        email=email,
        defaults={
            "risk": result.classification,
            "risk_score": result.risk_score,
            "reason": result.reason,
            "signals": {
                "signals": result.signals,
                "threat_categories": result.threat_categories,
            },
            "model": result.model,
            "status": status,
            "content_hash": content_hash,
            "prompt_version": settings.OPENAI_PROMPT_VERSION,
            "last_error": "",
            "analyzed_at": timezone.now(),
        },
    )
    if email.content_hash != content_hash:
        email.content_hash = content_hash
        email.save(update_fields=["content_hash", "updated_at"])
    return analysis


def analyze_email_locally(email: EmailRecord, *, force: bool = False) -> EmailAnalysis:
    if not force and hasattr(email, "analysis"):
        return email.analysis

    result = heuristic_analysis(
        email,
        "Basic local scan only. AI analysis has not been performed yet.",
    )
    return save_analysis_result(email, result)


def copy_cached_analysis(email: EmailRecord, cached: EmailAnalysis, *, content_hash: str) -> EmailAnalysis:
    analysis, _ = EmailAnalysis.objects.update_or_create(
        email=email,
        defaults={
            "risk": cached.risk,
            "risk_score": cached.risk_score,
            "reason": cached.reason,
            "signals": cached.signals,
            "model": cached.model,
            "status": EmailAnalysis.Status.COMPLETED,
            "content_hash": content_hash,
            "prompt_version": cached.prompt_version or settings.OPENAI_PROMPT_VERSION,
            "last_error": "",
            "analyzed_at": timezone.now(),
        },
    )
    if email.content_hash != content_hash:
        email.content_hash = content_hash
        email.save(update_fields=["content_hash", "updated_at"])
    return analysis


def analyze_email(email: EmailRecord, *, force: bool = False, bulk: bool = True) -> EmailAnalysis:
    model = settings.OPENAI_BULK_MODEL if bulk else settings.OPENAI_MODEL
    content_hash = analysis_content_hash(email)
    cached = reusable_analysis_for_hash(email, model=model, content_hash=content_hash)
    if cached and (force or not hasattr(email, "analysis") or cached.email_id == email.pk):
        return cached if cached.email_id == email.pk else copy_cached_analysis(email, cached, content_hash=content_hash)

    if not force and hasattr(email, "analysis"):
        current = email.analysis
        if current.status in {EmailAnalysis.Status.QUEUED, EmailAnalysis.Status.RUNNING}:
            return current
        if current.model not in LOCAL_MODELS:
            if not current.content_hash:
                current.content_hash = content_hash
                current.prompt_version = current.prompt_version or settings.OPENAI_PROMPT_VERSION
                current.status = current.status or EmailAnalysis.Status.COMPLETED
                current.save(update_fields=["content_hash", "prompt_version", "status", "updated_at"])
                if email.content_hash != content_hash:
                    email.content_hash = content_hash
                    email.save(update_fields=["content_hash", "updated_at"])
                return current
            if current.content_hash == content_hash:
                return current

    try:
        result = analyze_with_openai(email, bulk=bulk)
    except Exception as exc:
        result = heuristic_analysis(email, friendly_openai_failure(exc))
        analysis = save_analysis_result(email, result)
        analysis.status = EmailAnalysis.Status.FAILED
        analysis.last_error = str(exc)[:1000]
        analysis.attempts += 1
        analysis.save(update_fields=["status", "last_error", "attempts", "updated_at"])
        return analysis

    return save_analysis_result(email, result)
