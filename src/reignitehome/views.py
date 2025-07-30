from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
from conversation.utils.gpt import generate_comebacks
from django.urls import reverse
from conversation.models import ChatCredit

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
        # Check credits
        credits = request.session.get('chat_credits', 0)
        if credits <= 0:
            signup_url = reverse('account_signup')
            return JsonResponse({
                'error': 'You’re out of chat credits. Sign up to unlock unlimited replies.',
                'redirect_url': signup_url
            }, status=403)
        
        # Deduct one credit and update session
        request.session['chat_credits'] = credits - 1
        credits_left = request.session['chat_credits']

        data = json.loads(request.body)
        last_text = data.get('last-reply', '').strip()
        
        comebacks = generate_comebacks(last_text)
        return JsonResponse({
            'alex': comebacks.get("AlexTextGameCoach", ""),
            'credits_left':credits_left,
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)
