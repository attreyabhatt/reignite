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
    get_mobile_opener_user_prompt,
    get_mobile_reply_prompt,
    get_mobile_reply_user_prompt,
)

# Initialize Gemini client with the new unified SDK
client = genai.Client(api_key=config('GEMINI_API_KEY'))

# Model constants
GEMINI_PRO = "gemini-3-pro-preview"      # For openers (vision capable)
GEMINI_FLASH = "gemini-3-flash-preview"  # For replies (fast text generation)


def generate_mobile_openers_from_image(image_bytes: bytes, custom_instructions: str = "") -> Tuple[str, bool]:
    """
    Generate opener suggestions from profile image using Gemini Pro (vision).

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions

    Returns:
        Tuple of (JSON array string of openers, success boolean)
    """
    system_prompt = get_mobile_opener_prompt(custom_instructions)
    user_prompt = get_mobile_opener_user_prompt()

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
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(system_prompt),
                        image_part,
                        types.Part.from_text(user_prompt),
                    ]
                )
            ]
        )

        ai_reply = response.text.strip()

        if ai_reply:
            success = True
        else:
            ai_reply = json.dumps([
                {"message": "Sorry, I couldn't analyze the profile image."},
                {"message": "Try uploading a clearer screenshot."},
                {"message": "Make sure the profile details are visible."}
            ])

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
    Generate reply suggestions for mobile app using Gemini Flash.

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
        response, usage_info = _generate_gemini_response(system_prompt, user_prompt, model=GEMINI_FLASH)

        ai_reply = response.text.strip()

        if ai_reply:
            success = True
        else:
            ai_reply = json.dumps([
                {"message": "Sorry, I couldn't generate a comeback this time."},
                {"message": "Want to try rephrasing the situation?"},
                {"message": "Or paste a bit more context from the chat."}
            ])
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
    model: str = GEMINI_FLASH
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Core Gemini API wrapper for text-only generation.

    Args:
        system_prompt: The system/context prompt
        user_prompt: The user's request
        model: The model to use (defaults to GEMINI_FLASH)

    Returns:
        Tuple of (response object, usage info dict)
    """
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(system_prompt.strip()),
                    types.Part.from_text(user_prompt.strip()),
                ]
            )
        ]
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
    total_tokens = getattr(usage, "total_token_count", input_tokens + output_tokens)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }
