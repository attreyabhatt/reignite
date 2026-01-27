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
    prompt = f"""
    Analyze the following dating app conversation and generate 3 replies.
    Instructions ( Do this Internally ):
    For each potential reply, first write a "Strategy" sentence explaining why this is a good response (e.g., "This calls back to her previous joke" or "This validates her opinion while challenging her"). Then write the message.
    Conversation: {last_text}
    """
    
    return prompt


def get_mobile_reply_user_prompt():
    """
    Returns the user prompt for reply generation.
    """
    return """Return ONLY a JSON array with exactly 3 replies:
[{"message": "reply 1"}, {"message": "reply 2"}, {"message": "reply 3"}]

JSON array only, no extra text."""