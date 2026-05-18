import logging

from django.conf import settings

from api.models import EmailRecord

logger = logging.getLogger(__name__)


def redis_client():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def enqueue_email_analysis(email: EmailRecord) -> bool:
    if not settings.ANALYSIS_QUEUE_ENABLED:
        return False

    if hasattr(email, "analysis"):
        return False

    try:
        client = redis_client()
        email_id = str(email.pk)
        added = client.sadd(settings.ANALYSIS_QUEUE_DEDUP_KEY, email_id)
        if added:
            client.rpush(settings.ANALYSIS_QUEUE_NAME, email_id)
        return True
    except Exception as exc:
        logger.warning("Failed to enqueue email analysis: %s", exc)
        return False


def pop_email_analysis(timeout: int | None = None) -> int | None:
    client = redis_client()
    item = client.blpop(settings.ANALYSIS_QUEUE_NAME, timeout=timeout or settings.ANALYSIS_QUEUE_POP_TIMEOUT)
    if not item:
        return None
    _, email_id = item
    return int(email_id)


def mark_email_analysis_done(email_id: int) -> None:
    redis_client().srem(settings.ANALYSIS_QUEUE_DEDUP_KEY, str(email_id))
