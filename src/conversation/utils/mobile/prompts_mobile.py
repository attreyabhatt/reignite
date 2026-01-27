"""
Mobile-specific prompts for Gemini-powered AI generation.
"""


def get_mobile_opener_prompt(custom_instructions=""):
    """
    Returns the system prompt for generating openers from profile images.
    Uses XML-structured reasoning for better quality with Gemini 3 Pro.
    """
    prompt = """Generate 3 unique openers for a dating app based on the profile image provided."""

    return prompt


def get_mobile_opener_user_prompt():
    """
    Returns the user prompt for opener generation.
    """
    return """Return ONLY a JSON array with exactly 3 openers:
[{"message": "opener 1"}, {"message": "opener 2"}, {"message": "opener 3"}]

JSON array only, no extra text."""


def get_mobile_reply_prompt(last_text, custom_instructions=""):
    """
    Returns the system prompt for generating reply suggestions.
    Used by the 'Need Reply' feature with gemini-3-pro-preview.
    """
    prompt = f"""Analyze the following dating app conversation and generate 3 replies.

Conversation:
{last_text}"""

    return prompt


def get_mobile_reply_user_prompt():
    """
    Returns the user prompt for reply generation.
    """
    return """Return the output strictly as a JSON array of objects. Each object must have:
- tone: (e.g., "Witty", "Sincere", "Flirty")
- thinking: A brief explanation of why this reply fits the context.
- message: The actual text to send.

Example format:
[{"tone": "Witty", "thinking": "explanation", "message": "reply text"}]

JSON array only, no extra text."""