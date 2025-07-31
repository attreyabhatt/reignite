from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
from conversation.utils.gpt import generate_comebacks
from conversation.utils.custom_gpt import generate_custom_comeback
from conversation.utils.todd_gpt import generate_toddv_comeback
from django.urls import reverse
from conversation.models import ChatCredit

def home(request):
    if 'chat_credits' not in request.session:
        request.session['chat_credits'] = 5
        
    if 'screenshot_credits' not in request.session:
        request.session['screenshot_credits'] = 5
        
    current_chat_credits = request.session['chat_credits']
    current_screenshot_credits = request.session['screenshot_credits']
    context = {
        'chat_credits':current_chat_credits,
        'screenshot_credits':current_screenshot_credits
    }
    
    if request.user.is_authenticated:
        return redirect('conversation_home')
    return render(request, 'home.html',context)

def ajax_reply_home(request):
    if request.method == 'POST':
        # Check credits
        credits = request.session.get('chat_credits', 0)
        if credits <= 0:
            signup_url = reverse('account_signup')
            return JsonResponse({
                'error': 'You’re out of chat credits. Sign up to unlock unlimited replies.',
                'redirect_url': signup_url
            }, status=403)
        
        data = json.loads(request.body)
        last_text = data.get('last_text', '').strip()
        platform = data.get('platform', '').strip()
        what_happened = data.get('what_happened', '').strip()
        
        # Deduct one credit and update session
        request.session['chat_credits'] = credits - 1
        credits_left = request.session['chat_credits']
        
        # Generate your AI response (dummy below)
        comebacks = generate_comebacks(last_text)
        custom_comeback = generate_custom_comeback(last_text,platform,what_happened)
        todd_comeback = generate_toddv_comeback(last_text,platform,what_happened)
        
        response_data = {
            'alex': comebacks.get("AlexTextGameCoach", ""),
            'custom': custom_comeback,
            'toddv' : todd_comeback,
            'credits_left': credits_left,
        }
        return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def privacy_policy(request):
    return render(request, "policy/privacy_policy.html")

def terms_and_conditions(request):
    return render(request, "policy/terms_and_conditions.html")

def refund_policy(request):
    return render(request, "policy/refund_policy.html")
