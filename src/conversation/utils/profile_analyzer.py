import base64
from openai import OpenAI
from decouple import config
import time
from .custom_gpt import extract_usage

client = OpenAI(api_key=config('GPT_API_KEY'))

def analyze_profile_image(image_file):
    """Analyze a dating profile screenshot or photo to extract information"""
    img_bytes = image_file.read()

    mime = _detect_mime(img_bytes)

    print(f"[DEBUG] Analyzing profile image - MIME: {mime}, Size: {len(img_bytes)} bytes")

    data_url = _build_data_url(img_bytes, mime)

    prompt = """You are an image profiling assistant. Extract as much grounded, observable information as possible from the SINGLE provided dating profile photo, and output it as clean, human-readable TEXT (not JSON).

RULES (IMPORTANT):
- Only state what you can actually see. If unsure, write “Unclear” and optionally add “Maybe: …” with up to 2–3 possibilities.
- Transcribe any visible text exactly (best-effort): prompts, captions, signs, usernames, stickers, logos.
- Do NOT infer sensitive traits: age, ethnicity, nationality, religion, politics, sexuality, disability, medical conditions, income, etc.
- You may describe “vibe” only if supported by visible cues and include a confidence level (High/Med/Low).

OUTPUT FORMAT (TEXT ONLY):
Use this exact structure and keep it skimmable:

=== IMAGE PROFILE REPORT ===

Scene & background
- Indoor/Outdoor: ...
- Setting (what it looks like): ...
- Background details (3–8 bullets): ...
- Lighting / photo style: ...

Person (only what’s visible)
- How many people: ...
- Shot type: (selfie / mirror selfie / full-body / candid / group / professional / unclear)
- Expression/pose: ...
- Outfit (items + colors + patterns): ...
- Accessories (jewelry, sunglasses, bag, etc.): ...
- Hair (simple visible description): ...

Objects worth referencing (for openers)
- <object> — opener potential: High/Med/Low — why: ...
- <object> — opener potential: ...

Activity / context clues
- Activity/context: ... | Evidence: ... | Confidence: High/Med/Low

Composition hooks (useful for playful openers)
- Group photo: Yes/No
- Cropped-friend hint (random arm/ear etc.): Yes/No
- Photobomb vibe: Yes/No
- “Misdirect targets” (things you could pretend is her): ...

Text found in image (verbatim)
- “...”
- “...”

Top opener hooks (ranked, 8–12)
1) ...
2) ...
3) ...
(Each hook should be short, specific, and directly visible.)

Overall vibe (optional, evidence-based)
- Vibe: ... | Evidence: ... | Confidence: High/Med/Low

FINAL CHECK:
- Be specific.
- If it’s not visible, say “Unclear”.
Return ONLY this formatted text report.

"""

    start_time = time.time()

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }],
            max_tokens=800
        )

        usage_info = extract_usage(resp)
        print(f"[DEBUG] Profile analysis usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | total={usage_info['total_tokens']}")

        output = resp.choices[0].message.content.strip()
        elapsed = time.time() - start_time
        print(f"Profile analysis time: {elapsed:.2f} seconds")

        if not output or len(output) < 20:
            return "Unable to extract meaningful information from the image. Please try uploading a clearer profile screenshot or photo."

        return output

    except Exception as e:
        print(f"[ERROR] Profile analysis error: {str(e)}")
        return f"Failed to analyze image: {str(e)}"


def stream_profile_analysis_bytes(img_bytes):
    mime = _detect_mime(img_bytes)
    data_url = _build_data_url(img_bytes, mime)
    prompt = _get_profile_prompt()

    stream = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }],
        max_tokens=800,
        stream=True
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _detect_mime(img_bytes):
    if img_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if img_bytes.startswith(b'RIFF') and len(img_bytes) > 11 and img_bytes[8:12] == b'WEBP':
        return 'image/webp'
    if img_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    return 'image/jpeg'


def _build_data_url(img_bytes, mime):
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _get_profile_prompt():
    return """
    # Role & Objective
    You are a dating profile analyzer. Extract key details from this dating profile screenshot or photo that would be useful for crafting a personalized opener.

    # What to Extract
    Analyze the image and extract the following information if visible:
    
    1. **Visual Details**:
       - Physical appearance (hair color, style, distinctive features)
       - Clothing style or accessories
       - Setting/background (location, activity)
       - Any pets or objects in the photo
    
    2. **Profile Information** (if it's a profile screenshot):
       - Name (if visible)
       - Age
       - Bio text
       - Interests or hobbies mentioned
       - Occupation or education
       - Location
       - Prompts and answers (Hinge/Bumble style)
    
    3. **Personality Indicators**:
       - What vibe does the photo/profile give? (adventurous, creative, professional, fun-loving, etc.)
       - Any unique or interesting details that stand out
       - Activities or interests shown in photos
    
    # Output Format
    Provide a concise, natural description in paragraph form that highlights the most interesting and conversation-worthy details. Focus on:
    - 2-3 visual details that stand out
    - Any hobbies, interests, or personality traits evident
    - Unique or quirky elements that could be conversation starters
    
    Keep it conversational and under 150 words. This will be used to generate opener messages.
    
    # Example Output
    "She has curly brown hair and is wearing a vintage band t-shirt in what looks like a coffee shop. Her bio mentions she's a graphic designer who loves indie music and trying new coffee spots. She has a dog (golden retriever) in one of her photos. One of her Hinge prompts says her perfect Sunday involves farmers markets and brunch. She gives off creative, laid-back vibes and seems to appreciate good aesthetics."
    
    # Instructions
    - Be specific but concise
    - Focus on details that would make good conversation starters
    - Don't make assumptions beyond what's clearly visible
    - If it's just a photo with no profile text, focus on visual details and implied interests"""
