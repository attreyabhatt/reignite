from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config('GPT_API_KEY'))

PERSONAS = {
    "alex": {
            "name": "AlexTextGameCoach",
            "system": (
                "You are a confident, playful dating texter. Short messages, never needy. "
                "Tease, make bold assumptions, never chase. Keep it cocky-funny and polarizing."
            )
            },
}

user_prompt = '''Respond ONLY with a JSON array of 3 objects:
[{"message": "your text", "confidence_score": 0.95}, ...]
No extra text.'''

def generate_comebacks(conversation: str) -> str:
    messages = {}

    for key, persona in PERSONAS.items():
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": persona["system"]},
                {"role": "user", "content": (
                    f"Conversation:\n{conversation}\n\n"
                    "Write one short message to revive the conversation."
                )}
            ],
            temperature=0.9,
            max_tokens=150
        )
        messages[persona["name"]] = response.choices[0].message.content.strip()

    return messages
