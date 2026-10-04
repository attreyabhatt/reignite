"""Model-specific compatibility for Gemini request settings."""

from typing import Optional


VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}


def normalize_gemini_thinking_level(
    thinking_level: Optional[str],
    model: str,
    default: str = "high",
) -> str:
    level = (thinking_level or "").strip().lower()
    if level not in VALID_THINKING_LEVELS:
        level = default

    model = (model or "").strip().lower().removeprefix("models/")
    # Gemini 3.8 Flash rejects minimal; low is its lowest supported effort.
    if model == "gemini-3.8-flash" and level == "minimal":
        return "low"
    return level
