from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from .models import Conversation, ChatCredit, CopyEvent, GuestWebConversationAttempt, WebAppConfig

from conversation.utils.web.image_web import extract_conversation_from_image_web
from conversation.utils.web.custom_web import generate_web_response
from conversation.utils.web_guest_logging import log_guest_web_attempt

from django_ratelimit.decorators import ratelimit
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


def _is_htmx_request(request):
    return request.headers.get("HX-Request", "").lower() == "true"


def _render_htmx_error(request, message):
    return render(request, "conversation/partials/response_error.html", {"error_message": message})


def _json_error(msg, status=400, redirect_url=None):
    payload = {"error": msg}
    if redirect_url:
        payload["redirect_url"] = redirect_url
    return JsonResponse(payload, status=status)


def _get_web_config():
    return WebAppConfig.load()


def _read_reply_input(request):
    content_type = (request.content_type or "").split(";")[0].strip().lower()
    if content_type == "application/json":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body.") from exc
        return {
            "last_text": (data.get("last_text") or "").strip(),
            "situation": (data.get("situation") or "").strip(),
            "her_info": (data.get("her_info") or "").strip(),
        }

    return {
        "last_text": (request.POST.get("last_text") or request.POST.get("last-reply") or "").strip(),
        "situation": (request.POST.get("situation") or "").strip(),
        "her_info": (request.POST.get("her_info") or "").strip(),
    }


def _extract_json_array(raw_response):
    if isinstance(raw_response, list):
        return raw_response

    if isinstance(raw_response, dict):
        for key in ("suggestions", "responses", "data"):
            value = raw_response.get(key)
            if isinstance(value, list):
                return value
        raise ValueError("Model output did not contain a suggestions array.")

    if not isinstance(raw_response, str):
        raise ValueError("Model output is not valid JSON text.")

    text = raw_response.strip()
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    text = re.sub(r"^\s*json\s*", "", text, flags=re.IGNORECASE).strip()

    if text.startswith("["):
        candidate = text
    else:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("No JSON array found in model output.")
        candidate = match.group(0)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse model output JSON: {exc.msg}") from exc

    if not isinstance(parsed, list):
        raise ValueError("Model output JSON is not an array.")

    return parsed


def parse_suggestions(raw_response):
    parsed = _extract_json_array(raw_response)
    suggestions = []

    for item in parsed:
        message = ""
        confidence_value = None

        if isinstance(item, dict):
            message = str(item.get("message") or "").strip()
            confidence_raw = item.get("confidence_score")
            if confidence_raw is not None:
                try:
                    confidence_value = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence_value = None
        elif isinstance(item, str):
            message = item.strip()

        if not message:
            continue

        confidence_label = ""
        if confidence_value is not None:
            confidence_label = f"Confidence: {round(confidence_value * 100)}%"

        suggestions.append({
            "message": message,
            "confidence_score": confidence_value,
            "confidence_label": confidence_label,
        })

        if len(suggestions) >= 3:
            break

    if not suggestions:
        raise ValueError("No valid suggestions were found in the model output.")

    return suggestions


def _render_htmx_redirect(url):
    response = HttpResponse("")
    response["HX-Redirect"] = url
    return response


def _json_or_htmx_error(request, is_htmx, message, status=400):
    if is_htmx:
        return _render_htmx_error(request, message)
    return _json_error(message, status=status)


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
@ratelimit(key='ip', rate='50/d', block=True)
def ajax_reply(request):
    is_htmx = _is_htmx_request(request)
    endpoint = GuestWebConversationAttempt.Endpoint.CONVERSATIONS_AJAX_REPLY
    guest_input_payload = {
        "content_type": (request.content_type or "").split(";")[0].strip().lower(),
        "is_htmx": is_htmx,
    }

    try:
        data = _read_reply_input(request)
    except ValueError as exc:
        error_message = str(exc)
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.REQUEST_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(request, is_htmx, error_message, status=400)

    last_text = (data.get('last_text') or "").strip()
    situation = (data.get('situation') or "").strip()
    her_info = (data.get('her_info') or "").strip()
    guest_input_payload.update({
        "last_text": last_text,
        "situation": situation,
        "her_info": her_info,
    })

    if not last_text and situation != "just_matched":
        error_message = "Conversation text is required."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(request, is_htmx, error_message, status=400)
    if len(last_text) > MAX_LAST_TEXT:
        error_message = f"Conversation is too long (>{MAX_LAST_TEXT} chars). Please shorten it."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(
            request,
            is_htmx,
            error_message,
            status=400,
        )
    if not situation or len(situation) > MAX_SITUATION_LEN or situation not in ALLOWED_SITUATIONS:
        error_message = "Invalid 'situation' value."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(request, is_htmx, error_message, status=400)
    if len(her_info) > MAX_HER_INFO:
        error_message = f"'Her information' is too long (>{MAX_HER_INFO} chars)."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.VALIDATION_ERROR,
            http_status=400,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(
            request,
            is_htmx,
            error_message,
            status=400,
        )

    created = False
    convo = None
    credits_left = None

    if request.user.is_authenticated:
        chat_credit = request.user.chat_credit
        if chat_credit.balance < 1:
            pricing_url = reverse('pricing:pricing')
            if is_htmx:
                return _render_htmx_redirect(pricing_url)
            return JsonResponse({'redirect_url': pricing_url})

        convo = Conversation.objects.filter(user=request.user, content=last_text).first()
        if convo:
            convo.content = last_text
            convo.situation = situation
            convo.her_info = her_info
            convo.save()
        else:
            convo = Conversation.objects.create(
                user=request.user,
                content=last_text,
                situation=situation,
                her_info=her_info,
                girl_title=generate_title(last_text),
            )
            created = True

        try:
            custom_response, success = generate_web_response(last_text, situation, her_info)
        except Exception:
            return _json_or_htmx_error(request, is_htmx, "AI engine error. Please try again.", status=500)

        if not success:
            return _json_or_htmx_error(
                request,
                is_htmx,
                "AI failed to generate a proper response. Try again. No credit deducted.",
                status=500,
            )

        try:
            suggestions = parse_suggestions(custom_response)
        except ValueError as exc:
            return _json_or_htmx_error(request, is_htmx, f"Could not parse generated response: {exc}", status=500)

        chat_credit.balance = max(0, chat_credit.balance - 1)
        chat_credit.save()
        credits_left = chat_credit.balance

        payload = {
            "custom": custom_response,
            "suggestions": suggestions,
            "credits_left": credits_left,
        }
        if created:
            payload["new_conversation"] = {"id": convo.id, "girl_title": convo.girl_title}

        if not is_htmx:
            return JsonResponse(payload)

        html_response = render(request, "conversation/partials/response_suggestions.html", {"suggestions": suggestions})
        triggers = {
            "creditsUpdated": {"credits_left": credits_left},
        }
        if created:
            triggers["conversationCreated"] = {"id": convo.id, "girl_title": convo.girl_title}
        html_response["HX-Trigger"] = json.dumps(triggers)
        return html_response

    guest_limit = _get_web_config().guest_reply_limit
    credits = int(request.session.get('chat_credits', guest_limit))
    if credits < 1:
        signup_url = reverse('account_signup') + "?next=/conversations/&message=out_of_credits"
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.CREDITS_BLOCKED,
            http_status=403,
            input_payload=guest_input_payload,
            output_payload={"redirect_url": signup_url},
            error_message="Guest out of credits.",
        )
        if is_htmx:
            return _render_htmx_redirect(signup_url)
        return JsonResponse({'redirect_url': signup_url}, status=403)

    try:
        custom_response, success = generate_web_response(last_text, situation, her_info)
    except Exception:
        error_message = "AI engine error. Please try again."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.AI_ERROR,
            http_status=500,
            input_payload=guest_input_payload,
            output_payload={"error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(request, is_htmx, error_message, status=500)

    if not success:
        error_message = "AI failed to generate a proper response. Try again. No credit deducted."
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.AI_ERROR,
            http_status=500,
            input_payload=guest_input_payload,
            output_payload={"custom": custom_response, "error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(
            request,
            is_htmx,
            error_message,
            status=500,
        )

    try:
        suggestions = parse_suggestions(custom_response)
    except ValueError as exc:
        error_message = f"Could not parse generated response: {exc}"
        log_guest_web_attempt(
            request=request,
            endpoint=endpoint,
            status=GuestWebConversationAttempt.Status.PARSE_ERROR,
            http_status=500,
            input_payload=guest_input_payload,
            output_payload={"custom": custom_response, "error": error_message},
            error_message=error_message,
        )
        return _json_or_htmx_error(request, is_htmx, error_message, status=500)

    request.session['chat_credits'] = max(0, credits - 1)
    credits_left = request.session['chat_credits']

    payload = {
        "custom": custom_response,
        "suggestions": suggestions,
        "credits_left": credits_left,
    }
    log_guest_web_attempt(
        request=request,
        endpoint=endpoint,
        status=GuestWebConversationAttempt.Status.SUCCESS,
        http_status=200,
        input_payload=guest_input_payload,
        output_payload=payload,
    )

    if not is_htmx:
        return JsonResponse(payload)

    html_response = render(request, "conversation/partials/response_suggestions.html", {"suggestions": suggestions})
    html_response["HX-Trigger"] = json.dumps({
        "creditsUpdated": {"credits_left": credits_left},
    })
    return html_response


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
        request.session.setdefault('chat_credits', _get_web_config().guest_reply_limit)
        request.session.setdefault('screenshot_credits', 5)

        # Deduct one screenshot credit (floor at 0)
        if request.session['screenshot_credits'] <= 0:
            signup_url = reverse('account_signup')
            return _json_error(
                "Screenshot upload limit reached. Sign up to unlock unlimited uploads.",
                status=403, redirect_url=signup_url
            )
        request.session['screenshot_credits'] = max(0, request.session['screenshot_credits'] - 1)
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
        text = extract_conversation_from_image_web(screenshot_file)
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


@require_POST
@ratelimit(key='ip', rate='200/d', block=True)   # optional but nice for guests
def log_copy(request):
    # Parse JSON safely
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")

    situation = (data.get('situation') or "").strip()
    her_info = (data.get('her_info') or "").strip()
    conversation_text = (data.get('conversation_text') or "").strip()
    copied_message = (data.get('copied_message') or "").strip()
    convo_id = data.get('conversation_id')

    # Validation (reuse your existing limits/constants)
    if not copied_message:
        return _json_error("'copied_message' is required.")
    if not situation or len(situation) > MAX_SITUATION_LEN or situation not in ALLOWED_SITUATIONS:
        return _json_error("Invalid 'situation' value.")
    if len(her_info) > MAX_HER_INFO:
        return _json_error(f"'Her information' is too long (>{MAX_HER_INFO} chars).")
    if len(conversation_text) > MAX_LAST_TEXT:
        return _json_error(f"Conversation is too long (>{MAX_LAST_TEXT} chars).")

    # Allow guests
    user = request.user if request.user.is_authenticated else None

    # Only try to link a Conversation when logged in
    convo = None
    if user and convo_id and str(convo_id).isdigit():
        try:
            convo = Conversation.objects.get(pk=int(convo_id), user=user)
        except Conversation.DoesNotExist:
            convo = None

    # Persist the copy event (works for guests too)
    CopyEvent.objects.create(
        user=user,
        conversation=convo,
        situation=situation,
        her_info=her_info,
        conversation_text=conversation_text,
        copied_message=copied_message,
    )

    return JsonResponse({'ok': True})
