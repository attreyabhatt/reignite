from django.db.utils import OperationalError, ProgrammingError

from conversation.models import WebAppConfig


DEFAULT_WEB_GUEST_REPLY_LIMIT = 5
DEFAULT_WEB_SIGNUP_BONUS_CREDITS = 3


def web_marketing_limits(request):
    del request  # Unused; required by Django context processor signature.

    guest_limit = DEFAULT_WEB_GUEST_REPLY_LIMIT
    signup_bonus = DEFAULT_WEB_SIGNUP_BONUS_CREDITS

    try:
        cfg = WebAppConfig.load()
        guest_limit = int(cfg.guest_reply_limit or DEFAULT_WEB_GUEST_REPLY_LIMIT)
        signup_bonus = int(cfg.signup_bonus_credits or DEFAULT_WEB_SIGNUP_BONUS_CREDITS)
    except (OperationalError, ProgrammingError):
        pass

    return {
        "web_guest_reply_limit": guest_limit,
        "web_signup_bonus_credits": signup_bonus,
    }
