"""Keep guest credit balances in sync with the configured web allowance."""

from .models import WebAppConfig


GUEST_REPLIES_USED_KEY = "web_guest_replies_used"


def get_guest_chat_credits(request):
    limit = WebAppConfig.load().guest_reply_limit
    if GUEST_REPLIES_USED_KEY not in request.session:
        # Preserve the remaining balance when adopting an existing session.
        remaining = int(request.session.get("chat_credits", limit))
        request.session[GUEST_REPLIES_USED_KEY] = max(0, limit - remaining)

    remaining = max(0, limit - int(request.session[GUEST_REPLIES_USED_KEY]))
    if request.session.get("chat_credits") != remaining:
        request.session["chat_credits"] = remaining
    return remaining


def use_guest_chat_credit(request):
    if GUEST_REPLIES_USED_KEY not in request.session:
        get_guest_chat_credits(request)
    request.session[GUEST_REPLIES_USED_KEY] += 1
    return get_guest_chat_credits(request)
