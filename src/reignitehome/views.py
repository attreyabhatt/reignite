from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
from conversation.utils.reignite_gpt import generate_reignite_comeback
from reignitehome.utils.ip_check import get_client_ip
from django.urls import reverse
from reignitehome.models import TrialIP,ContactMessage
from django_ratelimit.decorators import ratelimit
from conversation.utils.custom_gpt import generate_custom_response
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_http_methods

# Whitelists (match your <select> values in home.html)
PLATFORM_ALLOWED = {
    "Tinder","Bumble","Hinge","Instagram DM","WhatsApp",
    "iMessage/SMS","Snapchat","Telegram","Facebook Messenger","Other",
}
WHAT_ALLOWED = {
    "She left me on read",
    "She replied, but I need help with my next message",
    "She replied with one word, then nothing",
    "She didn’t reply after my question",
    "She ghosted after I asked her out",
    "Conversation just fizzled",
    "She didn’t reply after my joke",
    "She ignored my compliment",
    "I sent something awkward",
    "No reply to my flirty message",
    "Not sure / Just stopped",
    "Other",
}

def home(request):
    if 'chat_credits' not in request.session:
        request.session['chat_credits'] = 5
        
    current_chat_credits = request.session['chat_credits']
    
    
    ip = get_client_ip(request)
    trial_record, created = TrialIP.objects.get_or_create(ip_address=ip)
        
    if not created and trial_record.trial_used:
        current_chat_credits = 0
        
    context = {
        'chat_credits':current_chat_credits,
    }
        
    
    if request.user.is_authenticated:
        return redirect('conversation_home')
    return render(request, 'home.html',context)


@ratelimit(key='ip', rate='10/d', block=True)   # keep your current limit
@require_POST
def ajax_reply_home(request):
    # 1) Quick size & content-type guards
    clen = int(request.META.get("CONTENT_LENGTH") or 0)
    if clen and clen > 32_768:
        return JsonResponse({"error": "Payload too large."}, status=413)
    if "application/json" not in (request.META.get("CONTENT_TYPE") or ""):
        return JsonResponse({"error": "Content-Type must be application/json."}, status=415)

    # 2) Trial/credits gate (your original logic)
    ip = get_client_ip(request)
    trial_record, created = TrialIP.objects.get_or_create(ip_address=ip)
    if not created and trial_record.trial_used:
        signup_url = reverse('account_signup')
        return JsonResponse({
            'error': 'You’re out of chat credits. Sign up to unlock unlimited replies.',
            'redirect_url': signup_url
        }, status=403)

    credits = request.session.get('chat_credits', 0)
    if credits <= 0:
        trial_record.trial_used = True
        trial_record.save()
        signup_url = reverse('account_signup')
        return JsonResponse({
            'error': 'You’re out of chat credits. Sign up to unlock unlimited replies.',
            'redirect_url': signup_url
        }, status=403)

    # 3) Parse JSON safely
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    last_text = (data.get('last_text') or "").strip()
    platform = (data.get('platform') or "").strip()
    what_happened = (data.get('what_happened') or "").strip()

    # 4) Validate fields
    if not (5 <= len(last_text) <= 1200):
        return JsonResponse({"error": "Please enter the full conversation."}, status=400)
    if platform not in PLATFORM_ALLOWED:
        return JsonResponse({"error": "Invalid platform."}, status=400)
    if what_happened not in WHAT_ALLOWED:
        return JsonResponse({"error": "Invalid what_happened."}, status=400)

    # 5) Call generator; deduct credit only on success
    try:
        custom_response, success = generate_reignite_comeback(last_text, platform, what_happened)
    except Exception:
        return JsonResponse({"error": "Generation failed. Try again."}, status=502)

    if not success:
        return JsonResponse({"error": "Generation failed. Try again."}, status=502)

    request.session['chat_credits'] = max(0, credits - 1)
    return JsonResponse({
        "custom": custom_response,
        "credits_left": request.session['chat_credits'],
    })



def contact_view(request):
    submitted = False
    if request.method == 'POST':
        reason = request.POST.get('reason')
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        email = request.POST.get('email')

        ContactMessage.objects.create(
            reason=reason,
            title=title,
            subject=subject,
            email=email
        )
        submitted = True  # Flag for thank you message

    return render(request, 'contact.html', {'submitted': submitted})


def privacy_policy(request):
    return render(request, "policy/privacy_policy.html")

def terms_and_conditions(request):
    return render(request, "policy/terms_and_conditions.html")

def refund_policy(request):
    return render(request, "policy/refund_policy.html")
