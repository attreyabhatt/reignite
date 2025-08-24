from openai import OpenAI
from decouple import config
import json
from .left_on_read import is_left_on_read
client = OpenAI(api_key=config('GPT_API_KEY'))
from .prompts import get_prompt_for_coach
from typing import Dict, Any, Optional
import tiktoken
from .dating.openers import get_openers
def generate_custom_response(last_text, situation, her_info):
    
    SITUATION_TO_COACH = {
    "just_matched": "opener_coach",
    "spark_interest": "spark_coach",
    "stuck_after_reply": "matthew",
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
    system_prompt = get_prompt_for_coach(coach_key, last_text, situation, her_info, example1=example1, example2=example2, example3=example3)

    user_prompt = """
    Respond only with a JSON array containing exactly three objects, following this structure for each:
    - "message": a string with the generated message
    - "confidence_score": a numeric value between 0 and 1 indicating your confidence in the message.

    Rules:
    - Do not use em dashes (—) in any of the messages.
    - Keep each variation short, natural, and in texting style.

    Example:
    [
    {"message": "Did I just break your texting app or are you this mysterious?", "confidence_score": 0.95},
    {"message": "You ghost better than I flirt. Is it a competition?", "confidence_score": 0.90},
    {"message": "I see you like to keep me on my toes.", "confidence_score": 0.88}
    ]

    Begin by reviewing your planned output for strict schema alignment. Respond with only the JSON array; do not include any extra explanation or text.
    """
    
    # situation : effort, verbosity, temperature
    SITUATION_TO_CONFIG = {
        "just_matched": ("minimal", "low"),
        "spark_interest": ("medium", "low"),
        "stuck_after_reply": ("medium", "medium"),
        "dry_reply": ("minimal", "low"),
        "she_asked_question": ("medium", "low"),
        "feels_like_interview": ("medium", "medium"),
        "sassy_challenge": ("minimal", "low"),
        "left_on_read": ("medium", "medium"),
        "reviving_old_chat": ("medium", "medium"),
        "recovering_after_cringe": ("high", "medium"),
        "ask_her_out": ("medium", "low"),
        "switching_platforms": ("medium", "low"),
    }
    
    
        
    success = False
    usage_info: Optional[Dict[str, Any]] = None
    try:
        # effort, verbosity = SITUATION_TO_CONFIG.get(situation, ("medium", "low"))
        effort = "low"
        verbosity = "low"
        # use the mapped effort/verbosity instead of hardcoding 'low'
        response, usage_info = generate_gpt_response(
            system_prompt, user_prompt, effort=effort, verbosity=verbosity, model="gpt-5",situation=situation, her_info=her_info
            )

        # Responses API helper – this is a plain string of the model’s text output
        ai_reply = (response.output_text or "").strip()

        if ai_reply:
            success = True
        else:
            # Fallback JSON (keeps your frontend parser happy)
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
        
    return ai_reply, success

def generate_gpt_response(system_prompt, user_prompt, effort='low', verbosity='low', model="gpt-5", situation='', her_info=''):
    full_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"
    # if situation == "just_matched":
    #     full_prompt = system_prompt

    response = client.responses.create(
        model=model,
        input=full_prompt,
        reasoning={"effort": effort},
        text={"verbosity": verbosity}
    )
    
    usage_info = extract_usage(response)
    print(f"[DEBUG] Actual usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | reasoning={usage_info['reasoning_tokens']} | cached={usage_info['cached_input_tokens']} | total={usage_info['total_tokens']}")

    return response, usage_info


def extract_usage(response):
    """Safely extract usage info from a Responses API result."""
    u = getattr(response, "usage", None)
    if not u:
        return {}

    # Helper to get attributes if present, else dict keys, else default
    def safe_get(obj, key, default=0):
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    input_tokens = safe_get(u, "input_tokens")
    output_tokens = safe_get(u, "output_tokens")
    total_tokens = safe_get(u, "total_tokens", input_tokens + output_tokens)
    reasoning_tokens = safe_get(u, "reasoning_tokens", 0)

    # Prompt caching details (optional)
    cached_tokens = 0
    prompt_tokens_details = safe_get(u, "prompt_tokens_details", None)
    if prompt_tokens_details:
        cached_tokens = safe_get(prompt_tokens_details, "cached_tokens", 0)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "cached_input_tokens": cached_tokens,
        "uncached_input_tokens": max(input_tokens - cached_tokens, 0)
    }
