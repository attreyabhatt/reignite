from openai import OpenAI
from decouple import config
import json
from .left_on_read import is_left_on_read
client = OpenAI(api_key=config('GPT_API_KEY'))
from .prompts import get_prompt_for_coach

def generate_custom_response(last_text, situation, her_info):
    
    # custom_gpt.py (top-level or separate config module)
    SITUATION_TO_COACH = {
        "just_matched": "marc",
        "responding_to_prompt": "logan",
        "stuck_after_reply": "matthew",
        "dry_reply": "marc",
        "she_asked_question": "logan",
        "feels_like_interview": "mark",
        "left_on_read": "corey",
        "reviving_old_chat": "marc",
        "recovering_after_cringe": "ken",
        "mixed_signals": "corey",
        "she_interested": "alex",
        "planning_date": "corey",
        "post_date_followup": "matthew",
        "switching_platforms": "marc"
    }

    coach_key = SITUATION_TO_COACH.get(situation, "marc")  # fallback to Marc
    system_prompt = get_prompt_for_coach(coach_key, last_text, situation, her_info)
    
    print("Coach Key: " + coach_key)
    print("System Prompt: " + system_prompt)

    user_prompt = '''
                Respond ONLY with a JSON array of 3 objects.
                Each object must have:
                - "message": the message
                - "confidence_score": a number between 0 and 1 indicating confidence in the text being sent

                Example output:
                [
                {"message": "Did I just break your texting app or are you this mysterious?", "confidence_score": 0.95},
                {"message": "You ghost better than I flirt. Is it a competition?", "confidence_score": 0.90},
                {"message": "I see you like to keep me on my toes.", "confidence_score": 0.88}
                ]
                Do not add any explanation, commentary, or text outside of this JSON array.
    '''
    
    success = False
    try:
        response = generate_gpt_response(system_prompt,user_prompt,model="gpt-5")
        print(response)
        ai_choice = response.choices[0].message
        
        if ai_choice and ai_choice.content:
            ai_reply = ai_choice.content.strip()
            success = True
        else:
            print("Safe response: " + str(response))
            ai_reply = json.dumps([
                {"message": "Sorry, I couldn't generate a comeback this time.", "confidence_score": 0}
            ])
    except Exception as e:
        print("OpenAI API error:", e)
        ai_reply = ""  # or error handling logic
        
    return ai_reply, success

def generate_gpt_response(system_prompt,user_prompt,model):
    response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.90,
    )
    return response



