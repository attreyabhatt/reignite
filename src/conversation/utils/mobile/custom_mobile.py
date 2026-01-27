"""
Mobile-specific Gemini wrapper for AI generation.
Mirrors the structure of custom_gpt.py but uses Google's Gemini models.
"""

from google import genai
from google.genai import types
from decouple import config
import json
from typing import Tuple, Optional, Dict, Any

from .prompts_mobile import (
    get_mobile_opener_prompt,
    get_mobile_reply_prompt,
    get_mobile_reply_user_prompt,
)

# Initialize Gemini client with the new unified SDK
client = genai.Client(api_key=config('GEMINI_API_KEY'))

# Model constants
GEMINI_PRO = "gemini-3-pro-preview"      # For openers and replies

# Config for image-based generation (openers) - with thinking and high resolution
IMAGE_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    thinking_config=types.ThinkingConfig(thinking_level="high"),
    media_resolution="media_resolution_high",
    temperature=1.0,
    top_p=0.95
)

# Config for text-only generation (replies) - with thinking
TEXT_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    thinking_config=types.ThinkingConfig(thinking_level="high"),
    temperature=1.0,
    top_p=0.95
)


def _validate_and_clean_json(text: str) -> str:
    """
    Validate and clean JSON response. Ensures it's a valid JSON array with message objects.
    """
    text = text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    # Parse and validate
    parsed = json.loads(text)

    # Ensure it's a list
    if not isinstance(parsed, list):
        raise ValueError("Response is not a JSON array")

    # Ensure each item has "message" key and clean up
    cleaned = []
    for item in parsed:
        if isinstance(item, dict) and "message" in item:
            cleaned.append({"message": str(item["message"])})
        elif isinstance(item, str):
            cleaned.append({"message": item})

    if not cleaned:
        raise ValueError("No valid messages in response")

    return json.dumps(cleaned)


def generate_mobile_openers_from_image(image_bytes: bytes, custom_instructions: str = "") -> Tuple[str, bool]:
    """
    Generate opener suggestions from profile image using Gemini Pro (vision).

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions

    Returns:
        Tuple of (JSON array string of openers, success boolean)
    """
    prompt = get_mobile_opener_prompt(custom_instructions)

    success = False
    try:
        # Create image part for vision
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg"
        )

        response = client.models.generate_content(
            model=GEMINI_PRO,
            contents=[
                prompt,
                image_part,
            ],
            config=IMAGE_CONFIG
        )

        ai_reply = _validate_and_clean_json(response.text)
        success = True

        # Log usage if available
        usage = getattr(response, "usage_metadata", None)
        if usage:
            print(f"[DEBUG] Gemini image opener usage | input={getattr(usage, 'prompt_token_count', 0)} | output={getattr(usage, 'candidates_token_count', 0)}")

    except Exception as e:
        print("Gemini API error (image opener):", e)
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating openers. Try again in a moment."}
        ])

    print(ai_reply)
    return ai_reply, success


def generate_mobile_response(
    last_text: str,
    situation: str,
    her_info: str = "",
    tone: str = "Natural",
    custom_instructions: str = ""
) -> Tuple[str, bool]:
    """
    Generate reply suggestions for mobile app using Gemini Pro.

    Args:
        last_text: The conversation text
        situation: The situation type (e.g., "mobile_stuck_reply_prompt")
        her_info: Information about her (optional)
        tone: The desired tone (Natural, Flirty, Funny, Serious)
        custom_instructions: Optional user-provided instructions

    Returns:
        Tuple of (JSON array string of replies, success boolean)
    """
    system_prompt = get_mobile_reply_prompt(last_text, custom_instructions)
    user_prompt = get_mobile_reply_user_prompt()

    success = False
    usage_info: Optional[Dict[str, Any]] = None

    try:
        response, usage_info = _generate_gemini_response(system_prompt, user_prompt, model=GEMINI_PRO)
        ai_reply = _validate_and_clean_json(response.text)
        success = True
    except Exception as e:
        print("Gemini API error:", e)
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating replies. Try again in a moment."}
        ])

    if usage_info:
        print("[USAGE]", usage_info)

    print(ai_reply)
    return ai_reply, success


def _generate_gemini_response(
    system_prompt: str,
    user_prompt: str,
    model: str = GEMINI_PRO
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Core Gemini API wrapper for text-only generation.

    Args:
        system_prompt: The system/context prompt
        user_prompt: The user's request
        model: The model to use (defaults to GEMINI_PRO)

    Returns:
        Tuple of (response object, usage info dict)
    """
    response = client.models.generate_content(
        model=model,
        contents=system_prompt.strip() + "\n\n" + user_prompt.strip(),
        config=TEXT_CONFIG
    )

    usage_info = _extract_usage(response)
    print(f"[DEBUG] Gemini usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | total={usage_info['total_tokens']}")

    return response, usage_info


def _extract_usage(response) -> Dict[str, Any]:
    """
    Safely extract usage info from Gemini response.

    Args:
        response: The Gemini API response object

    Returns:
        Dictionary with token usage information
    """
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    input_tokens = getattr(usage, "prompt_token_count", 0)
    output_tokens = getattr(usage, "candidates_token_count", 0)
    total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }
