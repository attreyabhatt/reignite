import logging

import requests
from django.conf import settings
from django.db.models import Q

from community.models import UserBlock

logger = logging.getLogger(__name__)

_ONESIGNAL_NOTIFICATIONS_URL = "https://api.onesignal.com/notifications"
_COMMENT_NOTIFICATION_TITLE = "Ooh, good answer... \U0001F440"
_COMMENT_NOTIFICATION_BODY = (
    "The community is cooking. Tap to see the latest reply to your post!"
)


def send_post_comment_notification(
    *,
    post_author_id: int | None,
    comment_author_id: int | None,
    post_id: int,
    comment_id: int,
) -> bool:
    """Best-effort transactional push for post-comment events."""
    enabled = getattr(settings, "ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED", True)
    if not enabled:
        logger.debug("Comment push disabled via ONESIGNAL_COMMENT_NOTIFICATIONS_ENABLED.")
        return False

    app_id = getattr(settings, "ONESIGNAL_APP_ID", "").strip()
    rest_api_key = getattr(settings, "ONESIGNAL_REST_API_KEY", "").strip()
    if not app_id or not rest_api_key:
        logger.debug("OneSignal keys missing; skipping comment push.")
        return False

    if post_author_id is None or comment_author_id is None:
        logger.debug(
            "Comment push skipped because author ids are missing. post_author_id=%s comment_author_id=%s",
            post_author_id,
            comment_author_id,
        )
        return False

    if post_author_id == comment_author_id:
        logger.debug("Comment push skipped for self-comment on post %s.", post_id)
        return False

    blocked = UserBlock.objects.filter(
        Q(blocker_id=post_author_id, blocked_user_id=comment_author_id)
        | Q(blocker_id=comment_author_id, blocked_user_id=post_author_id)
    ).exists()
    if blocked:
        logger.debug(
            "Comment push suppressed due to block relationship. post_author_id=%s comment_author_id=%s",
            post_author_id,
            comment_author_id,
        )
        return False

    headers = {
        "Authorization": f"Key {rest_api_key}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "app_id": app_id,
        "target_channel": "push",
        "include_aliases": {
            "external_id": [str(post_author_id)],
        },
        "headings": {"en": _COMMENT_NOTIFICATION_TITLE},
        "contents": {"en": _COMMENT_NOTIFICATION_BODY},
        "data": {
            "action": "community_comment",
            "post_id": post_id,
            "comment_id": comment_id,
        },
    }

    try:
        response = requests.post(
            _ONESIGNAL_NOTIFICATIONS_URL,
            headers=headers,
            json=payload,
            timeout=8,
        )
    except requests.RequestException:
        logger.warning(
            "OneSignal comment push request failed for post_id=%s comment_id=%s.",
            post_id,
            comment_id,
            exc_info=True,
        )
        return False

    if response.status_code >= 400:
        logger.warning(
            "OneSignal comment push failed with status=%s for post_id=%s comment_id=%s. body=%s",
            response.status_code,
            post_id,
            comment_id,
            response.text[:400],
        )
        return False

    return True
