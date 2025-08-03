import base64
from openai import OpenAI
from decouple import config
client = OpenAI(api_key=config('GPT-API-KEY'))

def extract_conversation_from_image(screenshot_file):
    img_bytes = screenshot_file.read()
    mime = screenshot_file.content_type or "image/png"
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    prompt = (
        "This is a screenshot of a conversation from a messaging/dating app."
        "Extract the conversation from this screenshot in a clear structured text format,"
        "labeling each message with 'you:' or 'her:' per sender. "
        "If it's ambiguous who said what, infer the speaker based on the layout (e.g., left/right message bubbles or usernames)."
        "Example:\n"
        "you: hi\nher: hello\nyou: how are you?\n"
    )

    resp = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url}
            ]
        }],
    )
    
    output = resp.output_text.strip()

    # Basic failsafe: check if it contains at least one labeled message
    if not any(label in output.lower() for label in ["you:", "her:", "them:", "me:", "hi", "hello"]):
        return "Failed to extract the conversation. Please try uploading the screenshot again. If it keeps happening, upload a cleaner screenshot."

    return output

