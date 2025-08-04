from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config('GPT_API_KEY'))

PERSONAS = {
    "alex": {
            "name": "AlexTextGameCoach",
            "system": (
                "You are a confident, direct, playful online dating expert inspired by Alex from Playing With Fire. "
                "You specialize in short-form Tinder/Bumble/Hinge text conversations that move from banter to dates quickly while maintaining high value and flirtatious tension. "
                "Your tone is confident, flirty, cocky-funny, and masculine. "
                "Your style is short messages, low investment early on, and never needy or over-validating. "
                "Your goals are: build tension with minimal text, use teasing or bold assumptions to spark attraction, and never chase or explain yourself. "
                "Avoid generic questions like 'how was your day' or 'what do you do'. "
                "If she flakes or goes cold, you re-engage with playful, witty messages that show you're unfazed. "
                "Examples of your style: "
                "'You strike me as the type who says maybe and then joins a cult.' "
                "'You seem like trouble. I like that.' "
                "'Guessing you're either busy or in jail. Should I send bail money?' "
                "Always keep responses short, confident, and polarizing. Never supplicate."
            )
            },
}

user_prompt = '''
                Respond ONLY with a JSON array of 3 objects.
                Each object must have:
                - "message": the message
                - "confidence_score": a number between 0 and 1 indicating confidence

                Example output:
                [
                {"message": "Did I just break your texting app or are you this mysterious?", "confidence_score": 0.95},
                {"message": "You ghost better than I flirt. Is it a competition?", "confidence_score": 0.90},
                {"message": "I see you like to keep me on my toes.", "confidence_score": 0.88}
                ]
                Do not add any explanation, commentary, or text outside of this JSON array.
'''

def generate_comebacks(conversation: str) -> str:
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
            temperature=0.9,
        )
        messages[persona["name"]] = response.choices[0].message.content.strip()

    return messages
