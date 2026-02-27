"""
Mobile-specific OCR extraction using Gemini Flash.
Mirrors the structure of image_gpt.py but uses Google's Gemini models.
Includes failsafe fallback to GPT-4.1-mini when Gemini fails.
"""

import base64
from io import BytesIO
from google import genai
from google.genai import types
from decouple import config
import time
from typing import Any, Dict
from PIL import Image

from .openai_mobile import extract_conversation_from_image_openai

# Initialize Gemini client
client = genai.Client(api_key=config('GEMINI_API_KEY'))

GEMINI_FLASH = "gemini-3-flash-preview"
GPT_MODEL = "gpt-4.1-mini-2025-04-14"
VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}


def _normalize_thinking_level(thinking_level: str, default: str = "low") -> str:
    level = (thinking_level or "").strip().lower()
    if level in VALID_THINKING_LEVELS:
        return level
    return default


def _extract_usage(response: Any) -> Dict[str, int]:
    def _to_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _read_usage_int(usage_obj: Any, *attr_names: str) -> int:
        for name in attr_names:
            value = getattr(usage_obj, name, None)
            if value is not None:
                return _to_int(value)
        return 0

    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens = _read_usage_int(
        usage,
        "prompt_token_count",
        "input_token_count",
    )
    output_tokens = _read_usage_int(
        usage,
        "candidates_token_count",
        "output_token_count",
    )
    thinking_tokens = _read_usage_int(
        usage,
        "thoughts_token_count",
        "thinking_token_count",
        "thought_token_count",
    )
    total_tokens = input_tokens + output_tokens + thinking_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": total_tokens,
    }


def extract_conversation_from_image_mobile(screenshot_file, thinking_level: str = "low"):
    """
    Extract conversation text from a screenshot using Gemini Flash with GPT-4.1-mini fallback.

    Fallback chain:
    1. Gemini Flash (resized image)
    2. Gemini Flash (original image)
    3. GPT-4.1-mini (fallback)

    Args:
        screenshot_file: Uploaded file object with .read() method
        thinking_level: Gemini thinking level (minimal/low/medium/high)

    Returns:
        Extracted conversation text with labels and timestamps
    """
    img_bytes = screenshot_file.read()
    original_bytes = len(img_bytes)
    thinking_level = _normalize_thinking_level(thinking_level)

    # Resize/compress large images to reduce latency and payload size
    resized_bytes = _resize_image_bytes(img_bytes)
    if len(resized_bytes) != original_bytes:
        print(f"[DEBUG] Resized image bytes: {original_bytes} -> {len(resized_bytes)}")

    mime = _detect_mime(img_bytes)
    print(f"[DEBUG] Using MIME type: {mime}")
    print(f"[DEBUG] File size: {len(resized_bytes)} bytes")

    prompt = _get_conversation_prompt()
    model_used = None

    # Attempt 1: Gemini Flash with resized image
    try:
        start_time = time.time()
        output, usage_info = _run_ocr_call(
            prompt,
            resized_bytes,
            mime,
            start_time,
            thinking_level=thinking_level,
        )

        # Failsafe: require labeled lines with a timestamp bracket
        if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
            raise ValueError("OCR output missing labeled lines")

        model_used = GEMINI_FLASH
        print(f"[AI-ACTION] action=ocr model_used={model_used} status=success")
        if usage_info:
            print("[USAGE]", usage_info)
        return output

    except Exception as e:
        print(f"[FAILSAFE] action=ocr attempt=1 model={GEMINI_FLASH} status=failed error={type(e).__name__}: {str(e)}")

    # Attempt 2: Gemini Flash with original image
    try:
        start_time = time.time()
        output, usage_info = _run_ocr_call(
            prompt,
            img_bytes,
            mime,
            start_time,
            thinking_level=thinking_level,
        )

        if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
            raise ValueError("OCR output missing labeled lines")

        model_used = GEMINI_FLASH
        print(f"[AI-ACTION] action=ocr model_used={model_used} status=success (original_image)")
        if usage_info:
            print("[USAGE]", usage_info)
        return output

    except Exception as e:
        print(f"[FAILSAFE] action=ocr attempt=2 model={GEMINI_FLASH} status=failed error={type(e).__name__}: {str(e)}")

    # Attempt 3: GPT-4.1-mini fallback
    try:
        print(f"[FAILSAFE] action=ocr attempt=3 model={GPT_MODEL} status=attempting")
        output = extract_conversation_from_image_openai(img_bytes, mime)

        if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
            raise ValueError("OCR output missing labeled lines")

        model_used = GPT_MODEL
        print(f"[AI-ACTION] action=ocr model_used={model_used} status=success")
        return output

    except Exception as e:
        print(f"[FAILSAFE] action=ocr attempt=3 model={GPT_MODEL} status=failed error={type(e).__name__}: {str(e)}")

    # All models failed
    print(f"[AI-ACTION] action=ocr model_used=none status=all_failed attempts=3")
    return ("Failed to extract the conversation with timestamps. Please try uploading the screenshot again. "
            "If it keeps happening, try a clearer, uncropped screenshot.")


def _run_ocr_call(prompt, img_bytes, mime, start_time, thinking_level: str = "low"):
    """Run OCR using Gemini Flash vision."""
    image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
    thinking_level = _normalize_thinking_level(thinking_level)

    response = client.models.generate_content(
        model=GEMINI_FLASH,
        contents=[prompt, image_part],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
        )
    )

    usage_info = _extract_usage(response)

    output = response.text.strip()
    elapsed = time.time() - start_time
    print(f"[DEBUG] Gemini OCR response time: {elapsed:.2f} seconds")

    return output, usage_info


def _resize_image_bytes(img_bytes, max_long_edge=1280, quality=85):
    """Resize image if too large."""
    try:
        with Image.open(BytesIO(img_bytes)) as img:
            width, height = img.size
            long_edge = max(width, height)

            # Keep small JPEGs as-is to avoid unnecessary recompression
            if long_edge <= max_long_edge and (img.format or '').upper() in ('JPEG', 'JPG'):
                return img_bytes

            if long_edge > max_long_edge:
                scale = max_long_edge / float(long_edge)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            out = BytesIO()
            img.save(out, format='JPEG', quality=quality, optimize=True)
            return out.getvalue()
    except Exception as exc:
        print(f"[WARN] Image resize failed: {exc}")
        return img_bytes


def _detect_mime(img_bytes):
    """Detect image MIME type from bytes."""
    if img_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if img_bytes.startswith(b'RIFF') and len(img_bytes) > 11 and img_bytes[8:12] == b'WEBP':
        return 'image/webp'
    if img_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    return 'image/jpeg'


def _get_conversation_prompt():
    """Get the OCR extraction prompt."""
    return """Extract the full conversation from the screenshot and output line-by-line text with sender labels and timestamps.

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
