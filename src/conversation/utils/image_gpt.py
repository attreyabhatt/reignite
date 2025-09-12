import base64
from openai import OpenAI
from decouple import config
import time
from .custom_gpt import extract_usage
client = OpenAI(api_key=config('GPT_API_KEY'))

def extract_conversation_from_image(screenshot_file):
    img_bytes = screenshot_file.read()
    mime = screenshot_file.content_type or "image/png"
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    prompt = """
    # Role & Objective
    Extract the full conversation from the screenshot and output line-by-line text with **sender labels and timestamps**.

    # Extraction Rules
    - Transcribe ALL visible messages exactly as written (no paraphrasing).
    - For EACH message, include a timestamp in square brackets right after the sender label if any time is visible for that message in the UI.
    - Accept valid timestamp forms exactly as shown: e.g., "9:14 PM", "21:14", "Yesterday 7:03 PM", "Mon, Aug 25 • 7:03 PM", "08/25/2025 19:03".
    - If a message has no visible time next to it, but there is a nearby date/time header chip for the group (e.g., "Yesterday • 9:14 PM"), apply that header time to the messages in that group when it is clearly implied by the UI.
    - If no time is visible or confidently implied for a message, leave the timestamp empty as "" (do NOT invent or infer new times).
    - Keep sender identification as 'you:' and 'her:'. If ambiguous, infer from bubble color/orientation/username.

    # Formatting
    - One message per line in this exact pattern:
      you [<timestamp>]: <message text>
      her [<timestamp>]: <message text>
    - If timestamp is unknown, leave it empty but keep the brackets:
      you []: <message text>
    - Preserve message order top-to-bottom as displayed in the screenshot.
    - Include system/join/leave or date separator lines only if they clearly carry text; label such lines as:
      system [<timestamp_or_empty>]: <text>
      (Use 'system' only for non-user messages like "You accepted the invite", date separators, etc.)

    # Validation
    - Before finishing, check that every message line matches the pattern:
      ^(you|her|system) \\[(.*?)\\]: .+$
    - Confirm that all visible messages have been transcribed.

    # Output
    - Output ONLY the transcribed lines, no commentary or bullets.
    """

    effort = "low"
    verbosity = "low"
    start_time = time.time()
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
    print(f"[DEBUG] Actual usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | reasoning={usage_info['reasoning_tokens']} | cached={usage_info['cached_input_tokens']} | total={usage_info['total_tokens']}")

    output = resp.output_text.strip()
    elapsed = time.time() - start_time
    print(f"Response time: {elapsed:.2f} seconds")

    # Failsafe: require labeled lines with a timestamp bracket
    # e.g., "you [", "her [", or "system ["
    if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
        return ("Failed to extract the conversation with timestamps. Please try uploading the screenshot again. "
                "If it keeps happening, try a clearer, uncropped screenshot.")

    return output
