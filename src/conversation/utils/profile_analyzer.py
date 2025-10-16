import base64
from openai import OpenAI
from decouple import config
import time
from .custom_gpt import extract_usage

client = OpenAI(api_key=config('GPT_API_KEY'))

def analyze_profile_image(image_file):
    """Analyze a dating profile screenshot or photo to extract information"""
    img_bytes = image_file.read()
    
    # Detect MIME type
    mime = 'image/jpeg'
    if img_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    elif img_bytes.startswith(b'RIFF') and len(img_bytes) > 11 and img_bytes[8:12] == b'WEBP':
        mime = 'image/webp'
    elif img_bytes.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    
    print(f"[DEBUG] Analyzing profile image - MIME: {mime}, Size: {len(img_bytes)} bytes")
    
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    prompt = """
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
    - If it's just a photo with no profile text, focus on visual details and implied interests
    """

    effort = "low"
    verbosity = "low"
    start_time = time.time()
    
    try:
        resp = client.responses.create(
            model="gpt-5",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url}
                ]
            }],
            reasoning={"effort": effort},
            text={"verbosity": verbosity}
        )

        usage_info = extract_usage(resp)
        print(f"[DEBUG] Profile analysis usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | reasoning={usage_info['reasoning_tokens']} | total={usage_info['total_tokens']}")

        output = resp.output_text.strip()
        elapsed = time.time() - start_time
        print(f"Profile analysis time: {elapsed:.2f} seconds")

        if not output or len(output) < 20:
            return "Unable to extract meaningful information from the image. Please try uploading a clearer profile screenshot or photo."

        return output
        
    except Exception as e:
        print(f"[ERROR] Profile analysis error: {str(e)}")
        return f"Failed to analyze image: {str(e)}"