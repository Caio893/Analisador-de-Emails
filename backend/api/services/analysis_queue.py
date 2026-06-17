import logging

from django.conf import settings
from django.utils import timezone

from api.models import EmailAnalysis, EmailRecord
from api.services.openai_analysis import LOCAL_MODELS, analysis_content_hash

logger = logging.getLogger(__name__)


def valkey_client(*, socket_timeout: float | None = None):
    import valkey

    timeout = (
        settings.VALKEY_SOCKET_TIMEOUT_SECONDS
        if socket_timeout is None
        else socket_timeout
    )
    return valkey.from_url(
        settings.VALKEY_URL,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=settings.VALKEY_SOCKET_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=timeout,
    )


def enqueue_email_analysis(email: EmailRecord) -> bool:
    if not settings.ANALYSIS_QUEUE_ENABLED:
        return False

    content_hash = analysis_content_hash(email)
    analysis = getattr(email, "analysis", None)
    if analysis and analysis.status in {EmailAnalysis.Status.QUEUED, EmailAnalysis.Status.RUNNING}:
        return False

    if (
        analysis
        and analysis.model not in LOCAL_MODELS
        and analysis.status == EmailAnalysis.Status.COMPLETED
        and analysis.content_hash == content_hash
        and analysis.prompt_version == settings.OPENAI_PROMPT_VERSION
    ):
        return False

    client = None
    try:
        client = valkey_client()
        email_id = str(email.pk)
        added = client.sadd(settings.ANALYSIS_QUEUE_DEDUP_KEY, email_id)
        if not added:
            return False
        client.rpush(settings.ANALYSIS_QUEUE_NAME, email_id)
        EmailAnalysis.objects.update_or_create(
            email=email,
            defaults={
                "risk": analysis.risk if analysis else EmailAnalysis.Risk.TRUSTED,
                "risk_score": analysis.risk_score if analysis else 0,
                "reason": analysis.reason if analysis else "Analise avancada enfileirada.",
                "signals": analysis.signals if analysis else {},
                "model": analysis.model if analysis else "",
                "status": EmailAnalysis.Status.QUEUED,
                "content_hash": content_hash,
                "prompt_version": settings.OPENAI_PROMPT_VERSION,
                "last_error": "",
                "analyzed_at": analysis.analyzed_at if analysis else timezone.now(),
            },
        )
        return True
    except Exception as exc:
        logger.warning("Failed to enqueue email analysis: %s", exc)
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def pop_email_analysis(timeout: int | None = None) -> int | None:
    pop_timeout = timeout or settings.ANALYSIS_QUEUE_POP_TIMEOUT
    socket_timeout = max(settings.VALKEY_SOCKET_TIMEOUT_SECONDS, pop_timeout + 5)
    client = valkey_client(socket_timeout=socket_timeout)
    try:
        item = client.blpop(settings.ANALYSIS_QUEUE_NAME, timeout=pop_timeout)
        if not item:
            return None
        _, email_id = item
        return int(email_id)
    finally:
        client.close()


def mark_email_analysis_done(email_id: int) -> None:
    client = valkey_client()
    try:
        client.srem(settings.ANALYSIS_QUEUE_DEDUP_KEY, str(email_id))
    finally:
        client.close()


def mark_email_analysis_running(email: EmailRecord) -> None:
    analysis = getattr(email, "analysis", None)
    content_hash = analysis_content_hash(email)
    EmailAnalysis.objects.update_or_create(
        email=email,
        defaults={
            "risk": analysis.risk if analysis else EmailAnalysis.Risk.TRUSTED,
            "risk_score": analysis.risk_score if analysis else 0,
            "reason": analysis.reason if analysis else "Analise avancada em andamento.",
            "signals": analysis.signals if analysis else {},
            "model": analysis.model if analysis else "",
            "status": EmailAnalysis.Status.RUNNING,
            "content_hash": content_hash,
            "prompt_version": settings.OPENAI_PROMPT_VERSION,
            "last_error": "",
            "analyzed_at": analysis.analyzed_at if analysis else timezone.now(),
            "attempts": (analysis.attempts if analysis else 0) + 1,
        },
    )
