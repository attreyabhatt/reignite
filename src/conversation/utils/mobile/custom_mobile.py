"""
Mobile-specific Gemini wrapper for AI generation.
Mirrors the structure of custom_gpt.py but uses Google's Gemini models.
Includes failsafe fallback to GPT-4.1-mini when Gemini fails.
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
from .openai_mobile import (
    generate_openers_from_image_openai,
    generate_replies_openai,
)

# Initialize Gemini client with the new unified SDK
client = genai.Client(api_key=config('GEMINI_API_KEY'))

# Model constants
GEMINI_PRO = "gemini-3-pro-preview"      # For openers (paid users)
GEMINI_FLASH = "gemini-3-flash-preview"  # For replies and free users
GPT_MODEL = "gpt-4.1-mini-2025-04-14"    # Fallback model

# Config factories — thinking level is now caller-supplied

def _make_text_config(thinking_level="high"):
    """Build a text-only Gemini config with the given thinking level."""
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        temperature=1.0,
        top_p=0.95,
    )

def _make_image_config(thinking_level="high"):
    """Build an image Gemini config with the given thinking level."""
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        media_resolution="media_resolution_high",
        temperature=1.0,
        top_p=0.95,
    )


def _validate_and_clean_json(text: str) -> str:
    """
    Validate and clean JSON response. Ensures it's a valid JSON array with message objects.
    Preserves additional fields like tone and thinking if present.
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

    # Ensure each item has "message" key, preserve other fields
    cleaned = []
    for item in parsed:
        if isinstance(item, dict) and "message" in item:
            clean_item = {"message": str(item["message"])}
            # Preserve optional fields if present
            if "tone" in item:
                clean_item["tone"] = str(item["tone"])
            if "thinking" in item:
                clean_item["thinking"] = str(item["thinking"])
            cleaned.append(clean_item)
        elif isinstance(item, str):
            cleaned.append({"message": item})

    if not cleaned:
        raise ValueError("No valid messages in response")

    return json.dumps(cleaned)


def _call_gemini_openers(image_bytes: bytes, custom_instructions: str, model: str, thinking_level: str = "high") -> str:
    """
    Call Gemini for opener generation.

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions
        model: Gemini model to use (GEMINI_PRO or GEMINI_FLASH)
        thinking_level: Thinking level (low/medium/high)

    Returns:
        Validated JSON string of openers

    Raises:
        Exception: If API call or validation fails
    """
    system_prompt = get_mobile_opener_prompt(custom_instructions)
    user_prompt = get_mobile_opener_user_prompt()

    # Create image part for vision
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg"
    )

    response = client.models.generate_content(
        model=model,
        contents=[
            system_prompt,
            image_part,
            user_prompt,
        ],
        config=_make_image_config(thinking_level)
    )

    ai_reply = _validate_and_clean_json(response.text)

    # Log usage if available
    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(f"[DEBUG] Gemini image opener usage | model={model} | input={getattr(usage, 'prompt_token_count', 0)} | output={getattr(usage, 'candidates_token_count', 0)}")

    return ai_reply


def _call_openai_openers(image_bytes: bytes, custom_instructions: str) -> str:
    """
    Call OpenAI GPT-4.1-mini for opener generation (fallback).

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions

    Returns:
        Validated JSON string of openers

    Raises:
        Exception: If API call or validation fails
    """
    ai_reply = generate_openers_from_image_openai(image_bytes, custom_instructions)
    return _validate_and_clean_json(ai_reply)


def generate_mobile_openers_from_image(
    image_bytes: bytes,
    custom_instructions: str = "",
    use_pro_model: bool = True,
    thinking_level: str = "high",
    use_gpt_only: bool = False,
) -> Tuple[str, bool]:
    """
    Generate opener suggestions from profile image with cascading fallback.

    Fallback chain:
    - use_gpt_only=True: GPT-4.1-mini only (skip Gemini)
    - Paid users (use_pro_model=True): Gemini Pro -> Gemini Flash -> GPT-4.1-mini
    - Free users (use_pro_model=False): Gemini Flash -> GPT-4.1-mini

    Args:
        image_bytes: Raw bytes of the profile image
        custom_instructions: Optional user-provided instructions
        use_pro_model: If True, use Gemini Pro first (paid users). If False, start with Flash (free/guests).
        thinking_level: Thinking level for Gemini (low/medium/high)
        use_gpt_only: If True, skip Gemini cascade and go straight to GPT

    Returns:
        Tuple of (JSON array string of openers, success boolean)
    """
    success = False
    ai_reply = None
    model_used = None

    # Build model cascade based on user tier
    if use_gpt_only:
        models = [GPT_MODEL]
    elif use_pro_model:
        models = [GEMINI_PRO, GEMINI_FLASH, GPT_MODEL]
    else:
        models = [GEMINI_FLASH, GPT_MODEL]

    # Try each model in sequence
    for i, model in enumerate(models, 1):
        try:
            if model.startswith('gemini'):
                ai_reply = _call_gemini_openers(image_bytes, custom_instructions, model, thinking_level=thinking_level)
            else:
                ai_reply = _call_openai_openers(image_bytes, custom_instructions)

            # Success!
            success = True
            model_used = model
            break

        except Exception as e:
            print(f"[FAILSAFE] action=openers attempt={i} model={model} status=failed error={type(e).__name__}: {str(e)}")
            continue

    # Log final result
    if success:
        print(f"[AI-ACTION] action=openers model_used={model_used} status=success")
    else:
        print(f"[AI-ACTION] action=openers model_used=none status=all_failed attempts={len(models)}")
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating openers. Try again in a moment."}
        ])

    print(ai_reply)
    return ai_reply, success


def _call_gemini_replies(last_text: str, custom_instructions: str, model: str = GEMINI_FLASH, thinking_level: str = "high") -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Call Gemini for reply generation.

    Args:
        last_text: The conversation text
        custom_instructions: Optional user-provided instructions
        model: Gemini model to use
        thinking_level: Thinking level (low/medium/high)

    Returns:
        Tuple of (validated JSON string, usage info dict)

    Raises:
        Exception: If API call or validation fails
    """
    system_prompt = get_mobile_reply_prompt(last_text, custom_instructions)
    user_prompt = get_mobile_reply_user_prompt()

    response, usage_info = _generate_gemini_response(system_prompt, user_prompt, model=model, thinking_level=thinking_level)
    ai_reply = _validate_and_clean_json(response.text)

    return ai_reply, usage_info


def _call_openai_replies(last_text: str, custom_instructions: str) -> str:
    """
    Call OpenAI GPT-4.1-mini for reply generation (fallback).

    Args:
        last_text: The conversation text
        custom_instructions: Optional user-provided instructions

    Returns:
        Validated JSON string of replies

    Raises:
        Exception: If API call or validation fails
    """
    ai_reply = generate_replies_openai(last_text, custom_instructions)
    return _validate_and_clean_json(ai_reply)


def generate_mobile_response(
    last_text: str,
    situation: str,
    her_info: str = "",
    tone: str = "Natural",
    custom_instructions: str = "",
    thinking_level: str = "high",
    use_gpt_only: bool = False,
) -> Tuple[str, bool]:
    """
    Generate reply suggestions for mobile app with cascading fallback.

    Fallback chain (default): Gemini Flash -> GPT-4.1-mini
    When use_gpt_only=True: GPT-4.1-mini only (skip Gemini)

    Args:
        last_text: The conversation text
        situation: The situation type (e.g., "mobile_stuck_reply_prompt")
        her_info: Information about her (optional)
        tone: The desired tone (Natural, Flirty, Funny, Serious)
        custom_instructions: Optional user-provided instructions
        thinking_level: Thinking level for Gemini (low/medium/high)
        use_gpt_only: If True, skip Gemini cascade and go straight to GPT

    Returns:
        Tuple of (JSON array string of replies, success boolean)
    """
    success = False
    ai_reply = None
    model_used = None
    usage_info: Optional[Dict[str, Any]] = None

    if use_gpt_only:
        models = [GPT_MODEL]
    else:
        models = [GEMINI_FLASH, GPT_MODEL]

    # Try each model in sequence
    for i, model in enumerate(models, 1):
        try:
            if model.startswith('gemini'):
                ai_reply, usage_info = _call_gemini_replies(last_text, custom_instructions, model=model, thinking_level=thinking_level)
            else:
                ai_reply = _call_openai_replies(last_text, custom_instructions)

            # Success!
            success = True
            model_used = model
            break

        except Exception as e:
            print(f"[FAILSAFE] action=replies attempt={i} model={model} status=failed error={type(e).__name__}: {str(e)}")
            continue

    # Log final result
    if success:
        print(f"[AI-ACTION] action=replies model_used={model_used} status=success")
        if usage_info:
            print("[USAGE]", usage_info)
    else:
        print(f"[AI-ACTION] action=replies model_used=none status=all_failed attempts={len(models)}")
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating replies. Try again in a moment."}
        ])

    print(ai_reply)
    return ai_reply, success


def _generate_gemini_response(
    system_prompt: str,
    user_prompt: str,
    model: str = GEMINI_PRO,
    thinking_level: str = "high"
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Core Gemini API wrapper for text-only generation.

    Args:
        system_prompt: The system/context prompt
        user_prompt: The user's request
        model: The model to use (defaults to GEMINI_PRO)
        thinking_level: Thinking level (low/medium/high)

    Returns:
        Tuple of (response object, usage info dict)
    """
    response = client.models.generate_content(
        model=model,
        contents=[
            system_prompt,
            user_prompt,
        ],
        config=_make_text_config(thinking_level)
    )

    usage_info = _extract_usage(response)
    print(f"[DEBUG] Gemini usage | model={model} | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | total={usage_info['total_tokens']}")

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
