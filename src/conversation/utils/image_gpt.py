import base64
from io import BytesIO
from openai import OpenAI
from decouple import config
import time
from PIL import Image
from .custom_gpt import extract_usage

client = OpenAI(api_key=config('GPT_API_KEY'))

def extract_conversation_from_image(screenshot_file):
    img_bytes = screenshot_file.read()
    original_bytes = len(img_bytes)

    # Resize/compress large images to reduce latency and payload size
    resized_bytes = _resize_image_bytes(img_bytes)
    if len(resized_bytes) != original_bytes:
        print(f"[DEBUG] Resized image bytes: {original_bytes} -> {len(resized_bytes)}")

    mime = _detect_mime(img_bytes)

    # Log for debugging
    print(f"[DEBUG] Original content_type: {screenshot_file.content_type}")
    print(f"[DEBUG] Using MIME type: {mime}")
    print(f"[DEBUG] File size: {len(resized_bytes)} bytes")
    print(f"[DEBUG] First 10 bytes: {resized_bytes[:10].hex()}")

    data_url = _build_data_url(resized_bytes, mime)
    prompt = _get_conversation_prompt()
    start_time = time.time()

    try:
        output = _run_ocr_call(prompt, data_url, start_time)

        # Failsafe: require labeled lines with a timestamp bracket
        if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
            raise ValueError("OCR output missing labeled lines")

        return output

    except Exception as e:
        # Retry with original bytes if resized attempt fails
        print(f"[WARN] OCR failed on resized image, retrying original: {str(e)}")
        try:
            data_url_full = _build_data_url(img_bytes, mime)
            output = _run_ocr_call(prompt, data_url_full, time.time())

            if not any(tag in output.lower() for tag in ("you [", "her [", "system [")):
                return ("Failed to extract the conversation with timestamps. Please try uploading the screenshot again. "
                        "If it keeps happening, try a clearer, uncropped screenshot.")

            return output
        except Exception as exc:
            print(f"[ERROR] OpenAI API error: {str(exc)}")
            return f"Failed to process image: {str(exc)}"


def stream_conversation_from_image_bytes(img_bytes, use_resize=True):
    mime = _detect_mime(img_bytes)
    payload_bytes = _resize_image_bytes(img_bytes) if use_resize else img_bytes
    data_url = _build_data_url(payload_bytes, mime)
    prompt = _get_conversation_prompt()

    for delta in _stream_ocr_call(prompt, data_url):
        yield delta


def _run_ocr_call(prompt, data_url, start_time):
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }],
        max_tokens=1500
    )

    usage_info = extract_usage(resp)
    print(f"[DEBUG] Actual usage | input={usage_info['input_tokens']} | output={usage_info['output_tokens']} | total={usage_info['total_tokens']}")

    output = resp.choices[0].message.content.strip()
    elapsed = time.time() - start_time
    print(f"Response time: {elapsed:.2f} seconds")

    return output


def _stream_ocr_call(prompt, data_url):
    stream = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }],
        max_tokens=1500,
        stream=True
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _resize_image_bytes(img_bytes, max_long_edge=1280, quality=85):
    try:
        with Image.open(BytesIO(img_bytes)) as img:
            width, height = img.size
            long_edge = max(width, height)

            # Keep small JPEGs as-is to avoid unnecessary recompression
            if long_edge <= max_long_edge and (img.format or '').upper() in ('JPEG', 'JPG'):
                return img_bytes

            if long_edge > max_long_edge:
                scale = max_long_edge / float(long_edge)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            out = BytesIO()
            img.save(out, format='JPEG', quality=quality, optimize=True)
            return out.getvalue()
    except Exception as exc:
        print(f"[WARN] Image resize failed: {exc}")
        return img_bytes


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


def _get_conversation_prompt():
    return """Extract the conversation from this screenshot.

Format each message as:
you [timestamp]: message
her [timestamp]: message
system [timestamp]: message

Rules:
- Use timestamps if visible (e.g., "9:14 PM"), otherwise leave empty: you []: message
- "you" = right-side/blue bubbles, "her" = left-side/gray bubbles
- "system" = date separators, notifications
- Transcribe exactly as written, top to bottom
- Output ONLY the formatted lines, no extra text"""
