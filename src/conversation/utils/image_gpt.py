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
        "Extract the conversation from this screenshot in a clear structured text format, "
        "labeling each message with 'you:' or 'her:' per sender. "
        "Example:\n"
        "you: hi\nher: hello\nyou: how are you?\n"
    )

    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url}
            ]
        }],
    )

    return resp.output_text.strip()
