import hashlib
import logging

from conversation.models import GuestWebConversationAttempt


logger = logging.getLogger(__name__)


def _ensure_session_key(request):
    session_key = request.session.session_key
    if session_key:
        return session_key

    request.session.save()
    return request.session.session_key or ""


def _hash_session_key(session_key):
    value = str(session_key or "").strip()
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_payload(payload):
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return {}
    return {"value": str(payload)}


def log_guest_web_attempt(
    request,
    endpoint,
    status,
    http_status,
    input_payload=None,
    output_payload=None,
    error_message="",
):
    if request.user.is_authenticated:
        return

    try:
        session_key_hash = _hash_session_key(_ensure_session_key(request))
        GuestWebConversationAttempt.objects.create(
            session_key_hash=session_key_hash,
            endpoint=endpoint,
            status=status,
            http_status=int(http_status),
            input_payload=_normalize_payload(input_payload),
            output_payload=_normalize_payload(output_payload),
            error_message=(error_message or "").strip(),
        )
    except Exception:
        logger.exception(
            "Failed to persist guest web attempt endpoint=%s status=%s",
            endpoint,
            status,
        )
