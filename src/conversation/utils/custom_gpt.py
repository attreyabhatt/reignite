from openai import OpenAI
from decouple import config
import json

client = OpenAI(api_key=config('GPT_API_KEY'))

def generate_custom_comeback(last_text, tone, goal):
    
    if not last_text.strip() or not tone.strip() or not goal.strip():
        return json.dumps([
            {"message": "Paste your chat and set the tone + goal first.", "confidence_score": 0.99}
        ]), False

    left_on_read = is_left_on_read(last_text)
    print("Left on Read:" + str(left_on_read))
    
    if left_on_read:
        context_hint = (
            "The match hasn't replied to your last message — you've been left on read. "
            "Handle this with charm: re-engage boldly, using playful wit or confident teasing. "
            "Never chase, never act needy. Your comeback should make silence look like *their* loss."
        )
    else:
        context_hint = ""
        
    TONE_MAP = {
        "playful": "playful and upbeat",
        "flirty": "lightly flirtatious and fun",
        "sincere": "genuine and thoughtful",
        "confident": "calm and self-assured",
        "mysterious": "a little reserved, intriguing",
        "funny": "humorous and clever"
    }

    GOAL_MAP = {
        "keep it going": "maintain the conversation flow",
        "increase flirtation": "add a bit more playful tension",
        "build emotional connection": "create a deeper personal connection",
        "suggest casual meetup": "hint at meeting up casually",
        "recover from bad message": "bounce back from an awkward or weak message",
        "playfully test her interest": "tease lightly to gauge interest"
    }

    
    tone_safe = TONE_MAP.get(tone.lower(), "playful and upbeat")
    goal_safe = GOAL_MAP.get(goal.lower(), "maintain the conversation flow")
    
    # last_text = make_conversation_safe_with_gpt(last_text)
    
    system_prompt = f"""
                You are an emotionally intelligent and charming assistant designed to help users in live dating conversations with concise and impactful responses.

                Your vibe? A modern conversationalist who values engaging and thoughtful exchanges. You're flirty, emotionally aware, and know how to spark curiosity and interest — whatever the moment calls for.
                Personality:
                - Confident, intriguing, and emotionally in control
                - Playful, smooth, and self-assured
                - Speaks in short, engaging bursts — no long lectures or awkward lines
                - Occasionally shows vulnerability, but only to build connection

                Your mission:
                - Suggest replies that keep the conversation moving — in the tone and direction the user desires
                - Never chase. Never over-explain.
                - Create emotionally engaging, clever, or witty responses that feel natural — not robotic

                Style Rules:
                - Be concise and focused—but when the moment calls for depth or sincerity, go a little longer
                - Don’t ask basic questions — say things that resonate
                - Be captivating, not inappropriate. Confident, not awkward
                - Assume the user wants to keep it flirty, unless otherwise stated
                        
                Here’s the context:
                    - Full conversation so far: {last_text}
                    - User’ desired Tone: {tone_safe}
                    - User’s goal for this reply: {goal_safe}
                """
                
    alex_prompt = f"""
            You are a bold, charismatic online dating expert modeled after Alex from *Playing With Fire*. You specialize in crafting high-impact, short-form conversations for dating apps like Tinder, Bumble, and Hinge. Your tone is cocky-funny, masculine, flirtatious, and emotionally untouchable.

            You keep messages short and punchy — minimal text, maximum tension. You never ask boring questions, never validate excessively, and never chase. You lead the interaction, tease confidently, and move things toward a date quickly while keeping things playful and polarizing.

            You re-engage with charm if she flakes or goes cold, always unfazed and witty. Your style thrives on bold assumptions, flirty banter, and playful tension — not logical conversations or small talk.

            {context_hint}
            
            Examples of your voice:
            - “You seem like trouble. I like that.”
            - “You strike me as the type who says ‘maybe’ and then joins a cult.”
            - “Guessing you’re either busy or in jail. Should I send bail money?”
            - “You’re giving off ‘reads horoscopes unironically’ energy.”

            Rules:
            - No generic questions like “How was your day?” or “What do you do?”
            - No over-explaining or apologizing.
            - No needy behavior.
            - Always be slightly unpredictable and in control.

            Your goal: build chemistry fast, escalate tension, and convert matches into real-life dates — all without trying too hard.
            Full conversation so far: 
            {last_text}
            
    """

                
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

    
    # Compose OpenAI API call
    # safe_system_prompt = make_prompt_safe_with_gpt(system_prompt)
    # print(safe_system_prompt)
    success = False
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Or "gpt-4" if preferred
            messages=[
                {"role": "system", "content": alex_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.90,  # Adjustable: higher = more playful
        )
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

def make_prompt_safe_with_gpt(system_prompt):
    prompt = f"""
        You're an assistant that helps prepare a a system prompt for safe AI processing.

        Instructions:
        - Rewrite this prmpt to remove or reword any language that could trigger safety filters (e.g. explicit, sexual, suggestive, or aggressive language)
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
    
import re

def is_left_on_read(text):
    """
    Robustly checks if you were left on read in a conversation string.
    Handles 'you:' or 'her:', any capitalization, extra spaces, and multi-line messages.
    Returns True if the last message is from 'you', else False.
    """
    # Regex: matches 'you' or 'her', optional spaces, colon, then message (possibly empty)
    pattern = re.compile(r'^(you|her)\s*:\s*', re.IGNORECASE)

    # Process each line, building full messages with sender
    messages = []
    current_sender = None
    current_message = ''
    for line in text.splitlines():
        if not line.strip():
            continue  # Skip blank lines

        match = pattern.match(line)
        if match:
            # Save previous message if exists
            if current_sender is not None:
                messages.append((current_sender, current_message.strip()))
            current_sender = match.group(1).lower()
            current_message = line[match.end():].strip()
        else:
            # Continuation of previous message
            current_message += '\n' + line.strip()

    # Add the last message
    if current_sender is not None:
        messages.append((current_sender, current_message.strip()))

    if not messages:
        return False

    # Check if last message is from 'you'
    return messages[-1][0] == 'you'


