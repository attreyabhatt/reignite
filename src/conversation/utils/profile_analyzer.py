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

    prompt = """Extract details from this dating profile image for crafting openers.

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
