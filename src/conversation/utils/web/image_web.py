"""
Web-specific OCR extraction with provider order from WebAppConfig.
"""

import time
from functools import lru_cache
from io import BytesIO
from typing import Any, Dict, Tuple, Union

from decouple import config
from google import genai
from google.genai import types
from PIL import Image

from conversation.models import WebAppConfig

from .openai_web import GPT_MODEL, extract_conversation_from_image_openai_web

GEMINI_FLASH = "gemini-3-flash-preview"
VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}
WEB_DEFAULT_THINKING = "minimal"


@lru_cache(maxsize=1)
def _get_client():
    return genai.Client(api_key=config("GEMINI_API_KEY"))


def _normalize_thinking_level(thinking_level: str, default: str = WEB_DEFAULT_THINKING) -> str:
    level = (thinking_level or "").strip().lower()
    if level in VALID_THINKING_LEVELS:
        return level
    return default


def _get_provider_order():
    config = WebAppConfig.load()
    return config.provider_order()


def _empty_usage() -> Dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "total_tokens": 0,
    }


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
        return _empty_usage()

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


def _contains_labeled_lines(output: str) -> bool:
    lowered = (output or "").lower()
    return any(tag in lowered for tag in ("you [", "her [", "system ["))


def extract_conversation_from_image_web(
    screenshot_file,
    thinking_level: str = WEB_DEFAULT_THINKING,
    return_meta: bool = False,
) -> Union[str, Tuple[str, bool, Dict[str, Any]]]:
    """
    Extract conversation text using configured provider order.
    Gemini provider uses resized+original attempts; GPT provider uses original image.
    """
    img_bytes = screenshot_file.read()
    if not img_bytes:
        failed_text = (
            "Failed to extract the conversation with timestamps. Please try uploading the screenshot again. "
            "If it keeps happening, try a clearer, uncropped screenshot."
        )
        if return_meta:
            return failed_text, False, {
                "model_used": "none",
                "thinking_used": _normalize_thinking_level(thinking_level),
                "usage": _empty_usage(),
                "source_type": "ai",
            }
        return failed_text

    original_bytes = len(img_bytes)
    thinking_level = _normalize_thinking_level(thinking_level)
    resized_bytes = _resize_image_bytes(img_bytes)
    if len(resized_bytes) != original_bytes:
        print(f"[DEBUG] Resized image bytes: {original_bytes} -> {len(resized_bytes)}")

    mime = _detect_mime(img_bytes)
    prompt = _get_conversation_prompt()

    gemini_attempts = [
        ("resized", resized_bytes),
        ("original", img_bytes),
    ]

    provider_order = _get_provider_order()

    for provider in provider_order:
        if provider == WebAppConfig.PROVIDER_GEMINI:
            for attempt_number, (attempt_name, payload) in enumerate(gemini_attempts, 1):
                try:
                    output, usage_info = _run_ocr_call(
                        prompt=prompt,
                        img_bytes=payload,
                        mime=mime,
                        start_time=time.time(),
                        thinking_level=thinking_level,
                    )
                    if not _contains_labeled_lines(output):
                        raise ValueError("OCR output missing labeled lines")

                    print(
                        f"[AI-ACTION] action=web_ocr model_used={GEMINI_FLASH} "
                        f"status=success attempt={attempt_number} payload={attempt_name}"
                    )
                    if return_meta:
                        return output, True, {
                            "model_used": GEMINI_FLASH,
                            "thinking_used": thinking_level,
                            "usage": usage_info or _empty_usage(),
                            "source_type": "ai",
                        }
                    return output
                except Exception as exc:
                    print(
                        f"[FAILSAFE] action=web_ocr attempt={attempt_number} model={GEMINI_FLASH} "
                        f"status=failed error={type(exc).__name__}: {str(exc)}"
                    )
            continue

        if provider == WebAppConfig.PROVIDER_GPT:
            try:
                print(f"[FAILSAFE] action=web_ocr model={GPT_MODEL} status=attempting")
                output, usage_info = extract_conversation_from_image_openai_web(
                    img_bytes=img_bytes,
                    mime=mime,
                    model=GPT_MODEL,
                    return_usage=True,
                )

                if not _contains_labeled_lines(output):
                    raise ValueError("OCR output missing labeled lines")

                print(
                    f"[AI-ACTION] action=web_ocr model_used={GPT_MODEL} "
                    f"status=success payload=original"
                )
                if return_meta:
                    return output, True, {
                        "model_used": GPT_MODEL,
                        "thinking_used": "n/a",
                        "usage": usage_info or _empty_usage(),
                        "source_type": "ai",
                    }
                return output
            except Exception as exc:
                print(
                    f"[FAILSAFE] action=web_ocr model={GPT_MODEL} "
                    f"status=failed error={type(exc).__name__}: {str(exc)}"
                )
            continue

    failed_text = (
        "Failed to extract the conversation with timestamps. Please try uploading the screenshot again. "
        "If it keeps happening, try a clearer, uncropped screenshot."
    )
    if return_meta:
        return failed_text, False, {
            "model_used": "none",
            "thinking_used": thinking_level,
            "usage": _empty_usage(),
            "source_type": "ai",
        }
    return failed_text


def _run_ocr_call(
    prompt: str,
    img_bytes: bytes,
    mime: str,
    start_time: float,
    thinking_level: str = WEB_DEFAULT_THINKING,
) -> Tuple[str, Dict[str, int]]:
    image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
    thinking_level = _normalize_thinking_level(thinking_level)

    response = _get_client().models.generate_content(
        model=GEMINI_FLASH,
        contents=[prompt, image_part],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
        ),
    )

    usage_info = _extract_usage(response)
    output = (response.text or "").strip()
    elapsed = time.time() - start_time
    print(f"[DEBUG] Web OCR response time: {elapsed:.2f} seconds")

    return output, usage_info


def _resize_image_bytes(img_bytes, max_long_edge=1280, quality=85):
    try:
        with Image.open(BytesIO(img_bytes)) as img:
            width, height = img.size
            long_edge = max(width, height)

            if long_edge <= max_long_edge and (img.format or "").upper() in ("JPEG", "JPG"):
                return img_bytes

            if long_edge > max_long_edge:
                scale = max_long_edge / float(long_edge)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)

            if img.mode != "RGB":
                img = img.convert("RGB")

            out = BytesIO()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            return out.getvalue()
    except Exception as exc:
        print(f"[WARN] Image resize failed: {exc}")
        return img_bytes


def _detect_mime(img_bytes):
    if img_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if img_bytes.startswith(b"RIFF") and len(img_bytes) > 11 and img_bytes[8:12] == b"WEBP":
        return "image/webp"
    if img_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return "image/jpeg"


def _get_conversation_prompt():
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
