"""
Mobile-specific prompts for Gemini-powered AI generation.
"""


def get_mobile_opener_prompt(custom_instructions=""):
    """
    Returns the system prompt for generating openers from profile images.
    Uses XML-structured reasoning for better quality with Gemini 3 Pro.
    """
    prompt = """<role>
You are an expert dating coach known for witty, high-success-rate openers.
</role>

<instructions>
1. **Analyze the Screenshot**: Look closely at the provided image. Identify:
   - Specific details in the photos (background landmarks, pets, activities, clothing style).
   - Text in the bio (interests, age, job, prompts).
2. **Identify Hooks**: Find 3 distinct "hooks" based on unique details found in step 1.
3. **Draft Openers**: Create 3 different types of openers based on these hooks
   - Opener 1 (Observational): A comment on a specific visual detail.
   - Opener 2 (Playful/Teasing): A lighthearted tease about something in their bio or photo.
   - Opener 3 (Question): An engaging question that is easy to answer but specific to their profile.
4. **Tone Check**: Ensure lines are casual, low-pressure.
</instructions>

<output_format>
Return ONLY a JSON array with exactly 3 openers:
[{"message": "opener 1"}, {"message": "opener 2"}, {"message": "opener 3"}]
</output_format>"""

    if custom_instructions:
        prompt += f"""

<custom_instructions>
{custom_instructions}
</custom_instructions>"""

    return prompt


def get_mobile_reply_prompt(last_text, custom_instructions=""):
    """
    Returns the system prompt for generating reply suggestions.
    Used by the 'Need Reply' feature with gemini-3-pro-preview.
    """
    prompt = f"""Generate 3 replies for a dating app based on the conversation below.

Conversation:
{last_text}"""

    if custom_instructions:
        prompt += f"""

Custom Instructions (MUST FOLLOW):
"{custom_instructions}"
"""

    return prompt


def get_mobile_reply_user_prompt():
    """
    Returns the user prompt for reply generation.
    """
    return """Return ONLY a JSON array with exactly 3 replies:
[{"message": "reply 1"}, {"message": "reply 2"}, {"message": "reply 3"}]

JSON array only, no extra text."""
