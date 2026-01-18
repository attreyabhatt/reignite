from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config('GPT_API_KEY'))

def make_prompt_safe_with_gpt(system_prompt):
    prompt = f"""Rewrite this prompt to remove language that could trigger safety filters.
Keep the original meaning and conversation formatting (e.g. "Her: ...", "You: ...").

Prompt to clean:
{system_prompt}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": "You rewrite prompts to be safe while preserving meaning."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        print("Sanitization API error:", e)
        return system_prompt  # fallback to original