from openai import OpenAI
from decouple import config

client = OpenAI(api_key=config('GPT_API_KEY'))

def make_prompt_safe_with_gpt(system_prompt):
    prompt = f"""
        You're an assistant that helps prepare a system prompt for safe AI processing.

        Instructions:
        - Rewrite this prompt to remove or reword any language that could trigger safety filters (e.g. explicit, sexual, suggestive, or aggressive language)
        - Keep the original tone and meaning as much as possible
        - Keep formatting of the conversation (e.g. "Her: ...", "You: ...") intact

        Here is the prompt to clean up:
        {system_prompt}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a responsible and creative assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        print("Sanitization API error:", e)
        return system_prompt  # fallback to original