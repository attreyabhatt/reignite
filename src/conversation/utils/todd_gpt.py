from openai import OpenAI
from decouple import config
client = OpenAI(api_key=config('GPT_API_KEY'))

def generate_toddv_comeback(conversation_text, platform, what_happened):
    system_prompt = f"""You're a dating strategist. Revive this stalled conversation.

Context:
- Platform: {platform}
- Situation: {what_happened}
- Conversation: {conversation_text}

Style: Confident, never chasing, low investment, use context from the chat. Frame yourself as the prize."""

    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Write one short, natural message to revive the conversation."}
        ],
        max_tokens=120,
        temperature=0.75,
    )
    return response.choices[0].message.content.strip()
