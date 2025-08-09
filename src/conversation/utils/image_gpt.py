import base64
from openai import OpenAI
from decouple import config
import time

client = OpenAI(api_key=config('GPT_API_KEY'))

def extract_conversation_from_image(screenshot_file):
    
    img_bytes = screenshot_file.read()
    # img_bytes, mime = preprocess_image_bytes(img_bytes)
    mime = screenshot_file.content_type or "image/png"
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    prompt = """
    # Role and Objective
    - Extract conversations from messaging or dating app screenshots, presenting them as clearly structured text.
    
    # Instructions
    - Accurately transcribe all text from the provided screenshot.
    - Label each line with 'you:' or 'her:' based on sender.
    - If sender identity is unclear, infer using visual cues (message bubble orientation, color, or usernames).
    - Format output as simple, line-by-line text per message.
    - Validate your extraction by confirming all visible messages have been transcribed and each message is appropriately labeled. If any ambiguity remains, briefly note internal checks before proceeding.
    - Example output:
    ```
    you: hi
    her: hello
    you: how are you?
    ```

    # Output Format
    - Plain text with sender labels for each message.

    # Verbosity
    - Output only the transcribed conversation; exclude any extraneous details.

    # Stop Conditions
    - Finish when the complete conversation is extracted and all messages are properly labeled.
    """
    effort = "low"
    verbosity = "low"
    start_time = time.time()
    resp = client.responses.create(
        model="gpt-5",  # ← upgraded from gpt-4o
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

    output = resp.output_text.strip()
    end_time = time.time()
    elapsed = end_time - start_time

    print(f"Response time: {elapsed:.2f} seconds")
    # Basic failsafe: check if it contains at least one labeled message
    if not any(label in output.lower() for label in ["you:", "her:", "them:", "me:", "hi", "hello"]):
        return ("Failed to extract the conversation. Please try uploading the screenshot again. "
                "If it keeps happening, upload a cleaner screenshot.")

   
    return output

from io import BytesIO
from PIL import Image

def preprocess_image_bytes(img_bytes, max_side=1440, quality=80):
    im = Image.open(BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        im = im.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    out = BytesIO()
    im.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue(), "image/jpeg"
