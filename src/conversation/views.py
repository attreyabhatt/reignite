from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .models import Conversation, ChatCredit

from conversation.utils.image_gpt import extract_conversation_from_image
from conversation.utils.custom_gpt import generate_custom_response

import json
import re

# --------- Helpers ---------
ALLOWED_SITUATIONS = {
    "just_matched", "spark_interest",
    "stuck_after_reply", "dry_reply", "she_asked_question",
    "feels_like_interview", "sassy_challenge", "spark_deeper_conversation",
    "pivot_conversation", "left_on_read", "reviving_old_chat",
    "recovering_after_cringe", "ask_her_out", "switching_platforms"
}

MAX_LAST_TEXT = 8000          # protect model + DB
MAX_HER_INFO = 4000
MAX_SITUATION_LEN = 150

def _json_error(msg, status=400, redirect_url=None):
    payload = {"error": msg}
    if redirect_url:
        payload["redirect_url"] = redirect_url
    return JsonResponse(payload, status=status)

def generate_title(last_text: str) -> str:
    """Generate a short title based on the latest 'her:' line or last line."""
    matches = re.findall(r'(?:^|\n)her\s*:\s*(.+)', last_text, re.IGNORECASE)
    if matches:
        snippet = matches[-1][:40]  # last match
    else:
        snippet = last_text.strip().split('\n')[-1][:40] if last_text.strip() else "Conversation"
    snippet = re.sub(r'\s+', ' ', snippet).strip().capitalize()
    return f"{snippet}..."

# --------- Views ---------
def conversation_home(request):
    if not request.user.is_authenticated:
        return redirect('home')

    conversations = Conversation.objects.filter(user=request.user).order_by('-last_updated')
    chat_credit = request.user.chat_credit
    context = {
        'conversations': conversations,
        'chat_credits': chat_credit.balance,
    }
    return render(request, 'conversation/index.html', context)


@require_POST
def ajax_reply(request):
    # Auth required
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401)

    # Credit check (before parsing heavy input)
    chat_credit = request.user.chat_credit
    if chat_credit.balance < 1:
        # Keep your existing pricing redirect behavior
        return JsonResponse({'redirect_url': reverse('pricing:pricing')})

    # Parse JSON safely
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")

    last_text = (data.get('last_text') or "").strip()
    situation = (data.get('situation') or "").strip()
    her_info = (data.get('her_info') or "").strip()

    # ---- Validation ----
    if not last_text and situation != "just_matched":
        return _json_error("Conversation text is required.")
    if len(last_text) > MAX_LAST_TEXT:
        return _json_error(f"Conversation is too long (>{MAX_LAST_TEXT} chars). Please shorten it.")
    if not situation or len(situation) > MAX_SITUATION_LEN or situation not in ALLOWED_SITUATIONS:
        return _json_error("Invalid 'situation' value.")
    if len(her_info) > MAX_HER_INFO:
        return _json_error(f"'Her information' is too long (>{MAX_HER_INFO} chars).")

    # Upsert conversation (title is generated once for new conversations)
    convo = Conversation.objects.filter(user=request.user, content=last_text).first()
    created = False
    if convo:
        convo.content = last_text
        convo.situation = situation
        convo.her_info = her_info
        convo.save()
    else:
        generated_title = generate_title(last_text)
        convo = Conversation.objects.create(
            user=request.user,
            content=last_text,
            situation=situation,
            her_info=her_info,
            girl_title=generated_title
        )
        created = True

    # ---- AI Call (no credit deduction unless success) ----
    try:
        custom_response, success = generate_custom_response(last_text, situation, her_info)
    except Exception as e:
        # Log if you want; return safe error to user
        return _json_error("AI engine error. Please try again.", status=500)

    if not success:
        return _json_error("AI failed to generate a proper response. Try again. No credit deducted.", status=500)

    # Deduct exactly 1 credit on success
    chat_credit.balance = max(0, chat_credit.balance - 1)
    chat_credit.save()

    resp = {
        "custom": custom_response,
        "credits_left": chat_credit.balance,
    }
    if created:
        resp["new_conversation"] = {
            "id": convo.id,
            "girl_title": convo.girl_title
        }
    return JsonResponse(resp)


def conversation_detail(request, pk):
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401)
    try:
        convo = Conversation.objects.get(pk=pk, user=request.user)
    except Conversation.DoesNotExist:
        return _json_error("Not found", status=404)

    return JsonResponse({
        'girl_title': convo.girl_title,
        'content': convo.content,
        'situation': convo.situation,
        'her_info': convo.her_info,
    })


@ratelimit(key='ip', rate='50/d', block=True)
def ocr_screenshot(request):
    if request.method != 'POST':
        return _json_error("Invalid request", status=400)

    # Auth / session credits
    if not request.user.is_authenticated:
        # Initialize session credits if missing
        request.session.setdefault('chat_credits', 5)
        request.session.setdefault('screenshot_credits', 5)

        # Deduct one screenshot credit (floor at 0)
        if request.session['screenshot_credits'] <= 0:
            signup_url = reverse('account_signup')
            return _json_error(
                "Screenshot upload limit reached. Sign up to unlock unlimited uploads.",
                status=403, redirect_url=signup_url
            )
        request.session['screenshot_credits'] = max(0, request.session['screenshot_credits'] - 1)

        # Check chat credits (for consistency with your flow)
        if request.session.get('chat_credits', 0) <= 0:
            signup_url = reverse('account_signup')
            return _json_error(
                "You’re out of chat credits. Sign up to unlock unlimited replies.",
                status=403, redirect_url=signup_url
            )
    else:
        chat_credit = request.user.chat_credit
        if chat_credit.balance < 1:
            return JsonResponse({'redirect_url': reverse('pricing:pricing')})

    # File validations
    screenshot_file = request.FILES.get('screenshot')
    if not screenshot_file:
        return _json_error("No file uploaded.", status=400)

    # Basic content-type & size checks (tune as needed)
    allowed_types = {'image/png', 'image/jpeg', 'image/webp', 'image/heic', 'image/heif'}
    content_type = getattr(screenshot_file, 'content_type', '') or ''
    if content_type.lower() not in allowed_types:
        return _json_error("Unsupported file type. Please upload PNG/JPEG/WEBP/HEIC.", status=400)

    max_bytes = 8 * 1024 * 1024  # 8MB
    if getattr(screenshot_file, 'size', 0) > max_bytes:
        return _json_error("File too large. Please keep under 8 MB.", status=400)

    try:
        text = extract_conversation_from_image(screenshot_file)
        if not text or not text.strip():
            return _json_error("OCR returned empty text. Try a clearer screenshot.", status=422)
        return JsonResponse({'ocr_text': text})
    except Exception:
        return _json_error("OCR failed. Please try again.", status=500)


@require_POST
def delete_conversation(request):
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401)

    convo_id = request.POST.get('id')
    if not convo_id or not str(convo_id).isdigit():
        return _json_error("Invalid conversation id.", status=400)

    try:
        convo = Conversation.objects.get(id=convo_id, user=request.user)
    except Conversation.DoesNotExist:
        return _json_error("Not found", status=404)

    convo.delete()
    return JsonResponse({'success': True})
