import json
import re
import time
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from api.models import EmailAnalysis, EmailRecord
from api.services.trusted_senders import trusted_sender_rule_for_email

CLASSIFICATIONS = {"trusted", "slightly_trusted", "suspicious", "dangerous"}

OPENAI_SYSTEM_PROMPT = (
    "Voce e um analista de seguranca de email. Analise o pacote JSON do email. "
    "Classifique o email como trusted, slightly_trusted, suspicious ou dangerous. "
    "Considere spam, phishing, malware, virus, spoofing, consistencia entre "
    "remetente/dominio e o texto legivel do corpo do email. "
    "Os campos reason e signals devem ser escritos em portugues brasileiro, "
    "de forma clara para usuarios no Brasil. Nao responda em ingles. "
    "Nao afirme que um anexo e malicioso sem metadados que sustentem esse risco. "
    "O campo body ja foi limpo para remover URLs brutas e deve ser tratado como "
    "conteudo textual legivel, nao como lista de links."
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
    domain = sender_domain_for_email(email)
    readable_body = readable_text_for_ai(email.body)
    return {
        "folder": email.folder,
        "subject": email.subject,
        "sender": {
            "name": email.from_name,
            "email": email.from_email,
        },
        "domain": domain,
        "body": limit_text(readable_body, settings.GMAIL_BODY_CHAR_LIMIT),
    }


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
            )
        except Exception as exc:
            if attempt >= attempts - 1 or not retryable_openai_error(exc):
                raise
            time.sleep(base_delay * (2**attempt))


def friendly_openai_failure(exc: Exception) -> str:
    if exc.__class__.__name__ == "RateLimitError":
        return "A analise avancada atingiu um limite temporario."
    return "A analise avancada nao pode ser concluida agora."


def analyze_with_openai(email: EmailRecord, *, bulk: bool = True) -> AnalysisResult:
    trusted_result = trusted_sender_analysis(email)
    if trusted_result:
        return trusted_result

    if not settings.OPENAI_ANALYSIS_ENABLED:
        return heuristic_analysis(email, "A analise avancada esta desativada.")

    if not settings.OPENAI_API_KEY:
        return heuristic_analysis(email, "A chave da OpenAI nao esta configurada.")

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
            "analyzed_at": timezone.now(),
        },
    )
    return analysis


def analyze_email_locally(email: EmailRecord, *, force: bool = False) -> EmailAnalysis:
    if not force and hasattr(email, "analysis"):
        return email.analysis

    result = heuristic_analysis(
        email,
        "Basic local scan only. AI analysis has not been performed yet.",
    )
    return save_analysis_result(email, result)


def analyze_email(email: EmailRecord, *, force: bool = False, bulk: bool = True) -> EmailAnalysis:
    if not force and hasattr(email, "analysis"):
        return email.analysis

    try:
        result = analyze_with_openai(email, bulk=bulk)
    except Exception as exc:
        result = heuristic_analysis(email, friendly_openai_failure(exc))

    return save_analysis_result(email, result)
