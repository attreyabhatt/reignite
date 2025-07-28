from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config('GPT-API-KEY'))

PERSONAS = {
    "todd": {
        "name": "Todd Valentine",
        "system": (
            "You are a confident, emotionally intelligent AI wingman trained in the principles of Todd Valentine. "
            "You help revive cold conversations using calibrated humor, subtle challenges, and frame control. "
            "Your tone is clever, outcome-independent, and high-value. Never sound needy. Never over-explain."
        )
    },
    "julien": {
        "name": "Julien Blanc",
        "system": (
            "You are a chaotic, high-energy AI wingman inspired by Julien Blanc (RSD Max). "
            "You break social patterns with humor, absurdity, and emotional spikes. Be unpredictable, bold, and fun. "
            "Don't hold back — but keep it just calibrated enough to not get blocked."
        )
    },
    "neil": {
        "name": "Neil Strauss",
        "system": (
            "You are a mysterious, witty AI wingman modeled after Neil Strauss from 'The Game'. "
            "You revive dead conversations using cold reads, storytelling, playful challenges, and confident misdirection. "
            "Your tone is intriguing, subtly cocky, and always high-status."
        )
    },
}


def generate_comebacks(conversation: str) -> dict:
    """
    Generate 3 comeback messages based on the same dead conversation,
    each written in the style of a different coach: Todd, Julien, Neil.
    Returns a dictionary: {persona_name: message}
    """
    messages = {}
    
    for key, persona in PERSONAS.items():
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": persona["system"]},
                {"role": "user", "content": (
                    f"Here's the conversation so far:\n{conversation}\n\n"
                    "Write one short, natural-sounding message to revive the conversation. "
                    "Make sure it fits your style and increases the chance she responds."
                )}
            ],
            temperature=0.85,
        )
        messages[persona["name"]] = response.choices[0].message.content.strip()

    return messages

