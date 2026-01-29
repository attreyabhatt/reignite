"""
Mobile-specific OpenAI wrapper for AI generation fallback.
Used when Gemini models fail - provides GPT-4.1-mini as backup.
"""

from openai import OpenAI
from decouple import config
import json
import base64
from typing import Tuple

from .prompts_mobile import (
    get_mobile_opener_prompt,
    get_mobile_opener_user_prompt,
    get_mobile_reply_prompt,
    get_mobile_reply_user_prompt,
)

# Initialize OpenAI client
client = OpenAI(api_key=config('GPT_API_KEY'))

# Model constant
GPT_MODEL = "gpt-4.1-mini-2025-04-14"


def generate_openers_from_image_openai(
    image_bytes: bytes,
    custom_instructions: str = ""
) -> str:
    """
    Generate opener suggestions from profile image using GPT-4.1-mini.
    Fallback for when Gemini models fail.

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions

    Returns:
        JSON array string of openers

    Raises:
        Exception: If API call fails (caller should handle)
    """
    # Encode image to base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    system_prompt = get_mobile_opener_prompt(custom_instructions)

    # Add formatting rules
    system_prompt += "\nNo em dashes. No dashes. Do not put single quotes around words unless necessary."

    if custom_instructions and custom_instructions.strip():
        system_prompt += f"""

User's custom instructions (MUST FOLLOW):
{custom_instructions.strip()}"""

    user_prompt = get_mobile_opener_user_prompt()

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        temperature=1.0,
        max_tokens=500
    )

    ai_reply = response.choices[0].message.content.strip()

    # Log usage
    usage = getattr(response, "usage", None)
    if usage:
        print(f"[DEBUG] OpenAI image opener usage | input={usage.prompt_tokens} | output={usage.completion_tokens}")

    return ai_reply


def generate_replies_openai(
    last_text: str,
    custom_instructions: str = ""
) -> str:
    """
    Generate reply suggestions using GPT-4.1-mini.
    Fallback for when Gemini Flash fails.

    Args:
        last_text: The conversation text
        custom_instructions: Optional user-provided instructions

    Returns:
        JSON array string of replies

    Raises:
        Exception: If API call fails (caller should handle)
    """
    system_prompt = get_mobile_reply_prompt(last_text, custom_instructions)

    # Add formatting rules
    system_prompt += "\nNo em dashes. No dashes. Do not put single quotes around words unless necessary."

    user_prompt = get_mobile_reply_user_prompt()

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=1.0,
        max_tokens=500
    )

    ai_reply = response.choices[0].message.content.strip()

    # Log usage
    usage = getattr(response, "usage", None)
    if usage:
        print(f"[DEBUG] OpenAI reply usage | input={usage.prompt_tokens} | output={usage.completion_tokens}")

    return ai_reply


def extract_conversation_from_image_openai(
    img_bytes: bytes,
    mime: str = "image/jpeg"
) -> str:
    """
    Extract conversation text from screenshot using GPT-4.1-mini vision.
    Fallback for when Gemini OCR fails.

    Args:
        img_bytes: Raw bytes of the screenshot image
        mime: MIME type of the image

    Returns:
        Extracted conversation text with labels and timestamps

    Raises:
        Exception: If API call fails (caller should handle)
    """
    # Encode image to base64
    base64_image = base64.b64encode(img_bytes).decode('utf-8')

    system_prompt = """Extract the full conversation from the screenshot and output line-by-line text with sender labels and timestamps.

Rules:
- Transcribe ALL visible messages exactly as written.
- For EACH message, include a timestamp in square brackets if visible.
- Keep sender identification as 'you:' and 'her:'. If ambiguous, infer from bubble color/orientation.
- If no time is visible, leave timestamp empty but keep brackets.

Format (one message per line):
you [<timestamp>]: <message text>
her [<timestamp>]: <message text>
system [<timestamp>]: <system message>

Output ONLY the transcribed lines, no commentary."""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the conversation from this screenshot."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        temperature=0.3,  # Lower temperature for OCR accuracy
        max_tokens=2000   # Higher limit for longer conversations
    )

    output = response.choices[0].message.content.strip()

    # Log usage
    usage = getattr(response, "usage", None)
    if usage:
        print(f"[DEBUG] OpenAI OCR usage | input={usage.prompt_tokens} | output={usage.completion_tokens}")

    return output
