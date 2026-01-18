from openai import OpenAI
from decouple import config
import json
from .left_on_read import is_left_on_read
client = OpenAI(api_key=config('GPT_API_KEY'))
from .prompts import get_prompt_for_coach
from typing import Dict, Any, Optional
import tiktoken
from .dating.openers import get_openers
def generate_custom_response(last_text, situation, her_info, tone="Natural"):

    SITUATION_TO_COACH = {
    "just_matched": "opener_coach",
    "spark_interest": "spark_coach",
    "stuck_after_reply": "stuck_reply_coach",
    "mobile_stuck_reply_prompt": "mobile_stuck_reply_coach",
    "dry_reply": "alex",
    "she_asked_question": "matthew",
    "feels_like_interview": "mark",
    "sassy_challenge": "shit_test",
    "spark_deeper_conversation": "logan",
    "pivot_conversation": "matthew",
    "left_on_read": "left_on_read_coach",
    "reviving_old_chat": "marc",
    "recovering_after_cringe": "ken",
    "ask_her_out": "corey",
    "switching_platforms": "marc",
}

    example1 = ''
    example2 = ''
    example3 = ''
    if situation == "just_matched":
        example1, example2, example3 = get_openers()

    coach_key = SITUATION_TO_COACH.get(situation, "logan")  # fallback to Marc
    system_prompt = get_prompt_for_coach(coach_key, last_text, situation, her_info, example1=example1, example2=example2, example3=example3, tone=tone)

    user_prompt = """Respond only with a JSON array of exactly 3 objects:
        [{"message": "your text", "confidence_score": 0.95}, ...]

        Rules:
        - No em dashes (—)
        - Don't use words chaos and energy.
        - Short, natural texting style
        - JSON array only, no extra text
        """

    success = False
    usage_info: Optional[Dict[str, Any]] = None
    try:
        response, usage_info = generate_gpt_response(system_prompt, user_prompt)

        ai_reply = response.choices[0].message.content.strip()

        if ai_reply:
            success = True
        else:
            ai_reply = json.dumps([
                {"message": "Sorry, I couldn't generate a comeback this time.", "confidence_score": 0.0},
                {"message": "Want to try rephrasing the situation?", "confidence_score": 0.0},
                {"message": "Or paste a bit more context from the chat.", "confidence_score": 0.0}
            ])
    except Exception as e:
        print("OpenAI API error:", e)
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating replies. Try again in a moment.", "confidence_score": 0.0}
        ])

    if usage_info:
        print("[USAGE]", usage_info)


    print(ai_reply)
    return ai_reply, success


def generate_gpt_response(system_prompt, user_prompt, model="gpt-4.1-mini-2025-04-14"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.8,
        max_tokens=300
    )

    usage_info = extract_usage(response)
    print(f"[DEBUG] Actual usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | total={usage_info['total_tokens']}")

    return response, usage_info


def extract_usage(response):
    """Safely extract usage info from Chat Completions API result."""
    u = getattr(response, "usage", None)
    if not u:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    input_tokens = getattr(u, "prompt_tokens", 0)
    output_tokens = getattr(u, "completion_tokens", 0)
    total_tokens = getattr(u, "total_tokens", input_tokens + output_tokens)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }
