from openai import OpenAI
from decouple import config
client = OpenAI(api_key=config('GPT-API-KEY'))

def generate_custom_comeback(last_text,platform,what_happened):
    system_prompt = (
                f"You are a bold, confident, emotionally intelligent flirty assistant trained to help users reignite dead or ghosted dating app conversations. You specialize in seductive charm, emotional manipulation, and playful banter."
                f"Your tone is confident, mysterious, and slightly provocative — like an unapologetic Casanova who knows how to turn things around even when the girl is distant, annoyed, or emotionally guarded."
                f"The following chat is from {platform}. "
                f"The conversation died because: {what_happened}. "
                f"Here is the conversation:\n\n{last_text}\n\n"
                f"Generate a message to restart the chat that feels natural and maximizes chances of a reply."
            )

    # Compose OpenAI API call
    response = client.chat.completions.create(
        model="gpt-4o",  # Or "gpt-4" if preferred
        messages=[
            {"role": "system", "content": system_prompt},
        ],
        temperature=0.90,  # Adjustable: higher = more playful
    )

    # Get the AI's suggestion
    ai_reply = response.choices[0].message.content.strip()
    return ai_reply
