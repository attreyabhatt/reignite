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

    prompt = """    You are a photo-to-text extractor for dating-profile images.

    TASK
    Given ONE image (a dating app photo) and optionally the on-image caption text, extract ONLY what is directly visible and useful for crafting witty/flirty openers later.

    WHAT TO EXTRACT (ONLY if visible):
    1) Caption text (exactly as shown, if any)
    2) Setting/background (indoor/outdoor + 2–5 concrete items/scene elements)
    3) Lighting + vibe descriptors (max 5 words, purely visual: e.g., “soft warm light”, “nighttime flash”)
    4) Outfit (type + color; patterns if clearly visible)
    5) Accessories (glasses/jewelry/hat/bag etc. + colors)
    6) Hairstyle (length + color + style)
    7) Photo type (selfie/mirror selfie/portrait/group photo) + camera angle (if obvious)
    8) Filters/effects (sparkles, beauty filter, etc.)
    9) Potential “props” list for openers: each should be a SINGLE concrete element from the image that could be referenced alone (e.g., “pink glasses”, “sparkle filter”, “caption: Don’t judge me”)

    IF AN IMAGE IS PROVIDED — EXTRACT (VISIBLE ONLY)

    caption_text
    - Exact caption text shown on the image (if any).

    photo_type
    - selfie / mirror selfie / portrait / group photo / candid / unclear

    angle
    - eye-level / high-angle / low-angle / unclear

    setting
    - indoor or outdoor + 2–5 concrete visible elements (room, wall, bar, street, etc.)

    lighting_vibe
    - max 5 purely visual descriptors (e.g., “soft light”, “warm”, “low contrast”)

    outfit
    - clothing type + color (+ pattern if clearly visible)

    accessories
    - glasses, jewelry, hat, bag, etc. + color if visible

    hair
    - color + length + style (only what is visible)

    filters_effects
    - sparkle, beauty filter, blur, etc.

    props_for_openers (IMAGE)
    - A list of SINGLE, standalone visual elements that could each be referenced alone
    - Examples: “pink glasses”, “sparkle filter”, “caption: don’t judge me”
    - Do NOT combine objects
    - 3–10 items max

    bio_text
    - Full bio text as written (verbatim)

    prompt_answers
    - Each prompt question + answer pair (verbatim)

    explicit_self_descriptors
    - Words/phrases she uses about herself (only if explicitly stated)

    tone_signals
    - From wording ONLY: playful / sarcastic / dry / earnest / confident / unclear

    recurring_themes
    - Hobbies, motifs, or repeated ideas explicitly mentioned

    text_based_props_for_openers (TEXT)

    SINGLE references usable as standalone hooks
    Examples: “horoscopes”, “coffee addiction”, “don’t judge me”, “travel pics”, “gym selfies”
    No interpretation, no merging ideas
    3–10 items max
    
    OUTPUT FORMAT (PLAIN TEXT ONLY)
    Return the information using the exact section headers below.
    No emojis. No commentary. No assumptions.

    Explicit self-descriptors

    CONSTRAINTS
    - props_for_openers must contain ONLY single, standalone items/ideas (do NOT combine objects).
    - Keep lists short: 3–10 props max.
    - No extra keys, no commentary."""

    start_time = time.time()

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
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
        model="gpt-4.1-nano",
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
    return """Extract details from this dating profile image for crafting openers.

EXTRACT (only what's visible):
- caption_text: exact text on image
- photo_type: selfie/portrait/group/candid
- setting: indoor/outdoor + visible elements
- outfit: clothing type + color
- accessories: glasses/jewelry/hat + color
- hair: color + length + style
- bio_text: verbatim if visible
- prompt_answers: Q&A pairs if visible
- props_for_openers: 3-10 single standalone elements (e.g., "pink glasses", "coffee shop", "dog")

Output as plain text with section headers. No emojis, no assumptions."""
