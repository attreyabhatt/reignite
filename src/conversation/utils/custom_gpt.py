from openai import OpenAI
from decouple import config
import json
from .left_on_read import is_left_on_read
client = OpenAI(api_key=config('GPT_API_KEY'))
from .prompts import get_prompt_for_coach

def generate_custom_response(last_text, situation, her_info):
    
    SITUATION_TO_COACH = {
    "just_matched": "marc",
    "spark_interest": "matthew",
    "stuck_after_reply": "matthew",
    "dry_reply": "alex",
    "she_asked_question": "matthew",
    "feels_like_interview": "mark",
    "sassy_challenge": "todd",
    "spark_deeper_conversation": "logan",
    "pivot_conversation": "matthew",
    "left_on_read": "alex",
    "reviving_old_chat": "marc",
    "recovering_after_cringe": "ken",
    "ask_her_out": "corey",
    "switching_platforms": "marc",
}
    
    
    coach_key = SITUATION_TO_COACH.get(situation, "marc")  # fallback to Marc
    system_prompt = get_prompt_for_coach(coach_key, last_text, situation, her_info)
    
    user_prompt = """
    Respond only with a JSON array containing exactly three objects, following this structure for each:
    - "message": a string with the generated message
    - "confidence_score": a numeric value between 0 and 1 indicating your confidence in the message.

    Do not use em dashes (—) in any of the messages.
    
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
    try:
        # effort, verbosity = SITUATION_TO_CONFIG.get(situation, ("medium", "low"))
        effort = "low"
        verbosity = "low"
        # use the mapped effort/verbosity instead of hardcoding 'low'
        response = generate_gpt_response(system_prompt, user_prompt, effort=effort, verbosity=verbosity, model="gpt-5")

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

    return ai_reply, success

def generate_gpt_response(system_prompt, user_prompt, effort='low', verbosity='low', model="gpt-5"):
    full_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"
    response = client.responses.create(
        model=model,
        input=full_prompt,
        reasoning={"effort": effort},
        text={"verbosity": verbosity}
    )

    return response


