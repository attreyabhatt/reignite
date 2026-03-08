"""
Web-specific OpenAI fallback helpers.
Used when Gemini Flash fails for web replies or OCR.
"""

import base64
from functools import lru_cache
from typing import Any, Dict, Tuple, Union

from decouple import config
from openai import OpenAI

from .prompts_web import (
    get_web_opener_prompt,
    get_web_opener_user_prompt,
    get_web_reply_prompt,
    get_web_reply_user_prompt,
)

GPT_MODEL = "gpt-4.1-mini-2025-04-14"


@lru_cache(maxsize=1)
def _get_client():
    return OpenAI(api_key=config("GPT_API_KEY"))


def _build_usage_info(response: Any) -> Dict[str, int]:
    usage = getattr(response, "usage", None)

    def _to_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    if not usage:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens = _to_int(getattr(usage, "prompt_tokens", 0))
    output_tokens = _to_int(getattr(usage, "completion_tokens", 0))
    thinking_tokens = 0
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "total_tokens": input_tokens + output_tokens + thinking_tokens,
    }


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


def _build_reply_prompts(
    last_text: str,
    situation: str,
    her_info: str,
    custom_instructions: str,
) -> Tuple[str, str]:
    situation = (situation or "").strip()
    context_block = _build_web_context(situation, her_info, custom_instructions)

    if situation == "just_matched":
        system_prompt = get_web_opener_prompt(custom_instructions=custom_instructions)
        user_prompt = get_web_opener_user_prompt()
    else:
        conversation = (last_text or "").strip() or "[No conversation provided]"
        system_prompt = get_web_reply_prompt(
            conversation,
            custom_instructions=custom_instructions,
        )
        user_prompt = get_web_reply_user_prompt()

    system_prompt = (
        f"{system_prompt.strip()}\n\n"
        f"Web context (must follow):\n{context_block}\n"
    )
    return system_prompt, user_prompt


def generate_replies_openai_web(
    last_text: str,
    situation: str,
    her_info: str = "",
    custom_instructions: str = "",
    model: str = GPT_MODEL,
    return_usage: bool = False,
) -> Union[str, Tuple[str, Dict[str, int]]]:
    """
    Generate web reply/openers text using GPT fallback.
    """
    system_prompt, user_prompt = _build_reply_prompts(
        last_text=last_text,
        situation=situation,
        her_info=her_info,
        custom_instructions=custom_instructions,
    )

    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=1.0,
        max_tokens=500,
    )

    ai_reply = response.choices[0].message.content.strip()
    usage_info = _build_usage_info(response)
    if return_usage:
        return ai_reply, usage_info
    return ai_reply


def extract_conversation_from_image_openai_web(
    img_bytes: bytes,
    mime: str = "image/jpeg",
    model: str = GPT_MODEL,
    return_usage: bool = False,
) -> Union[str, Tuple[str, Dict[str, int]]]:
    """
    Extract conversation text with labeled lines from a screenshot using GPT fallback.
    """
    base64_image = base64.b64encode(img_bytes).decode("utf-8")

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

    response = _get_client().chat.completions.create(
        model=model,
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
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    output = response.choices[0].message.content.strip()
    usage_info = _build_usage_info(response)
    if return_usage:
        return output, usage_info
    return output

