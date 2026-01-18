from openai import OpenAI
from decouple import config
import json

client = OpenAI(api_key=config('GPT_API_KEY'))

def generate_reignite_comeback(last_text, platform, what_happened):
    system_prompt = f"""You are a witty texting wingman helping revive stalled dating conversations.

Context:
- Platform: {platform}
- Situation: {what_happened}
- Conversation: {last_text}

Rules:
1. If convo was going well + short gap: Use minimal nudges like "??" or "👀"
2. If >24 hours or unclear: Playfully tease about vanishing (not needy)
3. If last text was hard to respond to: Cute, slightly self-deprecating
4. If dead for days/weeks: Bold, funny re-entry

Style: Short (1-2 lines max), playful, confident, never desperate or needy."""

    user_prompt = """Respond only with a JSON array of exactly 3 objects:
[{"message": "your text", "confidence_score": 0.95}, ...]

Rules:
- No em dashes (—)
- Short, natural texting style
- JSON array only, no extra text"""

    success = False
    try:
        response = generate_gpt_response(system_prompt, user_prompt)
        ai_reply = response.choices[0].message.content.strip()

        if ai_reply:
            success = True
        else:
            ai_reply = json.dumps([
                {"message": "Sorry, I couldn't generate a response this time.", "confidence_score": 0.0},
                {"message": "Want to try rephrasing the situation?", "confidence_score": 0.0},
                {"message": "Or paste a bit more context from the chat.", "confidence_score": 0.0}
            ])
    except Exception as e:
        print("OpenAI API error:", e)
        ai_reply = json.dumps([
            {"message": "We hit a hiccup generating replies. Try again in a moment.", "confidence_score": 0.0}
        ])

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
    return response
