"""Web-specific AI utilities for the conversation app."""

from .prompts_web import (
    get_web_opener_prompt,
    get_web_opener_user_prompt,
    get_web_reply_prompt,
    get_web_reply_user_prompt,
)

__all__ = [
    "get_web_opener_prompt",
    "get_web_opener_user_prompt",
    "get_web_reply_prompt",
    "get_web_reply_user_prompt",
]
