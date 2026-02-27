from rest_framework.authentication import TokenAuthentication


def normalize_authorization_header(request):
    """Normalize legacy/malformed Authorization headers to `Token <key>`."""
    raw_header = (request.META.get("HTTP_AUTHORIZATION") or "").strip()
    if not raw_header:
        return None

    parts = raw_header.split()
    if len(parts) < 2:
        return None

    scheme = parts[0].lower()
    if scheme not in {"token", "bearer"}:
        return None

    token_value = " ".join(parts[1:]).strip().strip("'\"")

    # Handle values like "Token Token <key>" / "Token Bearer <key>".
    while True:
        lowered = token_value.lower()
        if lowered.startswith("token "):
            token_value = token_value[6:].strip().strip("'\"")
            continue
        if lowered.startswith("bearer "):
            token_value = token_value[7:].strip().strip("'\"")
            continue
        break

    if not token_value or " " in token_value:
        return None

    normalized = f"Token {token_value}"
    if normalized != raw_header:
        request.META["HTTP_AUTHORIZATION"] = normalized
    return normalized


class LenientTokenAuthentication(TokenAuthentication):
    """
    Token auth that accepts minor legacy formatting variants in Authorization.
    """

    def authenticate(self, request):
        normalize_authorization_header(request)
        return super().authenticate(request)
