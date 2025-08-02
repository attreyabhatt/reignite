from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
from conversation.utils.custom_gpt import generate_custom_comeback
from reignitehome.utils.ip_check import get_client_ip
from django.urls import reverse
from conversation.models import ChatCredit
from reignitehome.models import TrialIP


def home(request):
    if 'chat_credits' not in request.session:
        request.session['chat_credits'] = 5
        
    current_chat_credits = request.session['chat_credits']
    context = {
        'chat_credits':current_chat_credits,
    }
    
    if request.user.is_authenticated:
        return redirect('conversation_home')
    return render(request, 'home.html',context)

def ajax_reply_home(request):
    if request.method == 'POST':
        
        ip = get_client_ip(request)
        trial_record, created = TrialIP.objects.get_or_create(ip_address=ip)
        
        if not created and trial_record.trial_used:
            signup_url = reverse('account_signup')
            return JsonResponse({
                'error': 'Screenshot upload limit reached. Sign up to unlock unlimited uploads.',
                'redirect_url': signup_url
            }, status=403)

        # Check credits
        credits = request.session.get('chat_credits', 0)
        if credits <= 0:
            trial_record.trial_used = True
            trial_record.save()
            signup_url = reverse('account_signup')
            return JsonResponse({
                'error': 'Screenshot upload limit reached. Sign up to unlock unlimited uploads.',
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
        # comebacks = generate_comebacks(last_text)
        # todd_comeback = generate_toddv_comeback(last_text,platform,what_happened)
        custom_response = generate_custom_comeback(last_text,platform,what_happened)
        print(last_text)
        response_data = {
        'custom': custom_response,
        'credits_left': credits_left,
        }
        
        
        # response_data = {
        #     'alex': comebacks.get("AlexTextGameCoach", ""),
        #     'custom': custom_comeback,
        #     'toddv' : todd_comeback,
        #     'credits_left': credits_left,
        # }
        return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def privacy_policy(request):
    return render(request, "policy/privacy_policy.html")

def terms_and_conditions(request):
    return render(request, "policy/terms_and_conditions.html")

def refund_policy(request):
    return render(request, "policy/refund_policy.html")
