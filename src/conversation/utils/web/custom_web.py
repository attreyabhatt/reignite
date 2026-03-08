"""
Web-specific Gemini wrapper for AI generation.
Uses web prompt builders with provider order from WebAppConfig.
"""

import json
from functools import lru_cache
from typing import Any, Dict, Tuple, Union

from decouple import config
from google import genai
from google.genai import types

from conversation.models import WebAppConfig

from .prompts_web import (
    get_web_opener_prompt,
    get_web_opener_user_prompt,
    get_web_reply_prompt,
    get_web_reply_user_prompt,
)
from .openai_web import GPT_MODEL, generate_replies_openai_web

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

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": input_tokens + output_tokens + thinking_tokens,
    }


def _parse_json_payload(text: str):
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model output.")

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start:end + 1])


def _validate_and_clean_json(text: str) -> str:
    parsed = _parse_json_payload(text)

    if isinstance(parsed, dict):
        for key in ("suggestions", "responses", "data"):
            value = parsed.get(key)
            if isinstance(value, list):
                parsed = value
                break

    if not isinstance(parsed, list):
        raise ValueError("Model output is not a JSON array.")

    cleaned = []
    for item in parsed:
        if isinstance(item, dict):
            message = str(item.get("message") or "").strip()
            if not message:
                continue
            payload = {"message": message}
            if "confidence_score" in item:
                payload["confidence_score"] = item.get("confidence_score")
            cleaned.append(payload)
        elif isinstance(item, str):
            message = item.strip()
            if message:
                cleaned.append({"message": message})

        if len(cleaned) >= 3:
            break

    if not cleaned:
        raise ValueError("No valid messages in model output.")

    return json.dumps(cleaned)


def _build_web_context(situation: str, her_info: str, custom_instructions: str) -> str:
    context_lines = [f"Situation: {(situation or '').strip() or 'unknown'}"]

    her_info = (her_info or "").strip()
    if her_info:
        context_lines.append(f"Her info: {her_info}")

    custom_instructions = (custom_instructions or "").strip()
    if custom_instructions:
        context_lines.append(f"User custom instructions: {custom_instructions}")

    if (situation or "").strip() == "just_matched":
        context_lines.append(
            "This is a first-message case. Produce opener-style messages, not follow-ups."
        )

    return "\n".join(context_lines)


def _build_prompts(last_text: str, situation: str, her_info: str, custom_instructions: str) -> Tuple[str, str]:
    situation = (situation or "").strip()
    context_block = _build_web_context(situation, her_info, custom_instructions)

    if situation == "just_matched":
        system_prompt = get_web_opener_prompt()
        user_prompt = get_web_opener_user_prompt()
    else:
        conversation = (last_text or "").strip()
        if not conversation:
            conversation = "[No conversation provided]"
        system_prompt = get_web_reply_prompt(conversation)
        user_prompt = get_web_reply_user_prompt()

    system_prompt = (
        f"{system_prompt.strip()}\n\n"
        f"Web context (must follow):\n{context_block}\n"
    )
    return system_prompt, user_prompt


def generate_web_response(
    last_text: str,
    situation: str,
    her_info: str = "",
    tone: str = "Natural",
    custom_instructions: str = "",
    return_meta: bool = False,
) -> Union[Tuple[str, bool], Tuple[str, bool, Dict[str, Any]]]:
    """
    Generate web suggestions using provider order from WebAppConfig.
    """
    del tone  # Kept for signature compatibility.

    success = False
    usage_info = _empty_usage()
    thinking_level = WEB_DEFAULT_THINKING
    model_used = "none"
    thinking_used = thinking_level

    provider_order = _get_provider_order()
    system_prompt = None
    user_prompt = None

    for provider in provider_order:
        if provider == WebAppConfig.PROVIDER_GEMINI:
            try:
                if system_prompt is None or user_prompt is None:
                    system_prompt, user_prompt = _build_prompts(
                        last_text=last_text,
                        situation=situation,
                        her_info=her_info,
                        custom_instructions=custom_instructions,
                    )

                response = _get_client().models.generate_content(
                    model=GEMINI_FLASH,
                    contents=[
                        system_prompt,
                        user_prompt,
                    ],
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level=_normalize_thinking_level(thinking_level)
                        ),
                        temperature=1.0,
                        top_p=0.95,
                    ),
                )

                ai_reply = _validate_and_clean_json(response.text or "")
                usage_info = _extract_usage(response)
                success = True
                model_used = GEMINI_FLASH
                thinking_used = thinking_level
                print(
                    f"[AI-ACTION] action=web_replies model_used={model_used} "
                    f"thinking={thinking_used} status=success"
                )
                print("[USAGE]", usage_info)
                break
            except Exception as exc:
                print(
                    f"[FAILSAFE] action=web_replies model={GEMINI_FLASH} "
                    f"status=failed error={type(exc).__name__}: {str(exc)}"
                )
                continue

        if provider == WebAppConfig.PROVIDER_GPT:
            try:
                fallback_reply, fallback_usage = generate_replies_openai_web(
                    last_text=last_text,
                    situation=situation,
                    her_info=her_info,
                    custom_instructions=custom_instructions,
                    model=GPT_MODEL,
                    return_usage=True,
                )
                ai_reply = _validate_and_clean_json(fallback_reply)
                usage_info = fallback_usage or _empty_usage()
                success = True
                model_used = GPT_MODEL
                thinking_used = "n/a"
                print(
                    f"[AI-ACTION] action=web_replies model_used={model_used} "
                    f"thinking={thinking_used} status=success"
                )
                print("[USAGE]", usage_info)
                break
            except Exception as fallback_exc:
                print(
                    f"[FAILSAFE] action=web_replies model={GPT_MODEL} "
                    f"status=failed error={type(fallback_exc).__name__}: {str(fallback_exc)}"
                )
                continue

    if not success:
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating replies. Try again in a moment."}
        ])

    meta = {
        "model_used": model_used if success else "none",
        "thinking_used": thinking_used if success else thinking_level,
        "usage": usage_info,
        "source_type": "ai",
    }

    if return_meta:
        return ai_reply, success, meta
    return ai_reply, success
