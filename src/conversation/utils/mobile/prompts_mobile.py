"""
Mobile-specific prompts for Gemini-powered AI generation.
"""


def get_mobile_opener_prompt(custom_instructions=""):
    """
    Returns the system prompt for generating openers from profile images.
    Uses XML-structured reasoning for better quality with Gemini 3 Pro.
    """
    
    # hidden custom instruction from the mobile app also being sent here
    prompt = """Generate 3 unique openers for a dating app based on the profile image provided.

"""
    if custom_instructions and custom_instructions.strip():
        prompt += f"""User's custom instructions:
{custom_instructions.strip()}
"""

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
    # hidden custom instruction from the mobile app also being sent here
    prompt = f"""Generate 3 unique replies for a dating app based on the screenshot of the conversation provided.

Conversation:
{last_text}

"""

    if custom_instructions and custom_instructions.strip():
        prompt += f"""

User's custom instructions:
{custom_instructions.strip()}"""

    return prompt


def get_mobile_reply_user_prompt():
    """
    Returns the user prompt for reply generation.
    """
    return """Return ONLY a JSON array with exactly 3 replies:
[{"message": "reply 1"}, {"message": "reply 2"}, {"message": "reply 3"}]

JSON array only, no extra text."""


def get_mobile_reply_from_image_prompt(custom_instructions=""):
    """
    Returns the system prompt for generating replies from conversation screenshots.
    """
    prompt = """Generate 3 unique replies for a dating app based on the screenshot provided.

"""
    if custom_instructions and custom_instructions.strip():
        prompt += f"""User's custom instructions:
{custom_instructions.strip()}
"""
    return prompt


def get_mobile_reply_from_image_user_prompt():
    """
    Returns the user prompt for image-based reply generation.
    """
    return """Return ONLY a JSON array with exactly 3 replies:
[{"message": "reply 1"}, {"message": "reply 2"}, {"message": "reply 3"}]

JSON array only, no extra text."""