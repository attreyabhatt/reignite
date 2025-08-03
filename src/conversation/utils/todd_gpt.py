from openai import OpenAI
from decouple import config
client = OpenAI(api_key=config('GPT_API_KEY'))

def generate_toddv_comeback(conversation_text, platform, what_happened):
    

    system_prompt = f"""
You are an advanced dating strategist inspired by Todd Valentine (RSD Todd).
Given a stalled or dead dating conversation, analyze it like Todd would—identify the last “hook point,” missed opportunities, and current vibe.

Craft a single reply that:
- Uses logical, context-aware re-engagement (pivot or callback, not random humor)
- Frames the user as the prize (never chasing, never apologizing, never justifying)
- Subtly qualifies the girl (“let’s see if she can keep up,” or playful challenge)
- Is meta-aware (“Looks like we both got busy being interesting people…”)
- Keeps things low investment (no emotional chasing; easy for her to reply)
- Avoids canned lines—use real context from the chat, reference her interests if possible

Here’s the situation:
- Platform: {platform}
- What happened: {what_happened}
- Full conversation so far:
{conversation_text}

Example Output:
- “Alright, you’re officially the reigning champ of cliffhangers. Should I be impressed or worried?”
- “I see you’re testing my patience. That’s cute. Now, tell me: what’s something you’re actually passionate about?”
- “You seem mysteriously quiet… Plotting world domination, or just picking the perfect meme?”

Carefully review the conversation and deliver a Todd-style, logical, and high-value re-engagement message that makes her want to respond.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": (
                    f"Write one short, natural-sounding message to revive the conversation."
                )}
                  ],
        max_tokens=120,
        temperature=0.75,
    )
    return response.choices[0].message.content.strip()
