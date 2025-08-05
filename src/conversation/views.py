from django.shortcuts import render,redirect
from .models import Conversation, ChatCredit
from reignitehome.models import TrialIP
from django.urls import reverse
from django.http import JsonResponse
import json
from conversation.utils.image_gpt import extract_conversation_from_image
from conversation.utils.custom_gpt import generate_custom_response
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
import re

# Create your views here.
def conversation_home(request):
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(user=request.user).order_by('-last_updated')
        chat_credit = request.user.chat_credit
        if conversations:
            context = {
                'conversations': conversations,
                'chat_credits' : chat_credit.balance,
                }
            return render(request, 'conversation/index.html',context)
        
        context = {
                'chat_credits' : chat_credit.balance,
                }
        return render(request, 'conversation/index.html',context)
    
    return redirect('home')

def ajax_reply(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        chat_credit = request.user.chat_credit
        if chat_credit.balance < 1:
            return JsonResponse({'redirect_url': reverse('pricing:pricing')})

        data = json.loads(request.body)
        from datetime import datetime

        last_text = data.get('last_text', '').strip()
        situation = data.get('situation', '').strip()
        her_info = data.get('her_info', '').strip()

        print(her_info)
        
        conversation = Conversation.objects.filter(user=request.user, content=last_text).first()

        if conversation:
            # Update conversation (but keep the original title)
            conversation.content = last_text
            conversation.situation = situation
            conversation.her_info = her_info
            conversation.save()
            created = False
        else:
            # Generate title ONCE from the message
            generated_title = generate_title(last_text)

            conversation = Conversation.objects.create(
                user=request.user,
                content=last_text,
                situation=situation,
                her_info=her_info,
                girl_title=generated_title
            )
            created = True


        # Generate AI response
        custom_response, success = generate_custom_response(last_text,situation,her_info)
        print(custom_response)
        
        # Validate success before deducting credit
        if success:
            chat_credit.balance -= 1
            chat_credit.save()
        else:
            return JsonResponse({'error': 'AI failed to generate a proper response. Try again. No credit deducted.'}, status=500)
        
        
        response_data = {
        'custom': custom_response,
        'credits_left': chat_credit.balance,
        }
        
        # If it was just created, send back ID and title
        if created:
            response_data['new_conversation'] = {
                'id': conversation.id,
                'girl_title': conversation.girl_title
            }

        return JsonResponse(response_data)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def conversation_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        convo = Conversation.objects.get(pk=pk, user=request.user)
        return JsonResponse({
            'girl_title': convo.girl_title,
            'content': convo.content,
            'situation': convo.situation,
            'her_info': convo.her_info,
        })
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

@ratelimit(key='ip', rate='50/d', block=True)
def ocr_screenshot(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            if 'chat_credits' not in request.session:
                    request.session['chat_credits'] = 5
            if 'screenshot_credits' not in request.session:
                    request.session['screenshot_credits'] = 5
            
            # Deduct one screenshot credit session
            request.session['screenshot_credits'] = request.session['screenshot_credits'] - 1
            screenshot_credits_credits_left = request.session['screenshot_credits']
            
            if screenshot_credits_credits_left <= 0:
                signup_url = reverse('account_signup')
                return JsonResponse({
                    'error': 'Screenshot upload limit Reached. Sign up to unlock unlimited uploads.',
                    'redirect_url': signup_url
                }, status=403)
                
            # Check credits
            credits = request.session.get('chat_credits', 0)
            if credits <= 0:
                signup_url = reverse('account_signup')
                return JsonResponse({
                    'error': 'You’re out of chat credits. Sign up to unlock unlimited replies.',
                    'redirect_url': signup_url
                }, status=403)
                
        else:    
            chat_credit = request.user.chat_credit
            if chat_credit.balance < 1:
                return JsonResponse({'redirect_url': reverse('pricing:pricing')})        
            
        screenshot_file = request.FILES.get('screenshot')
        if not screenshot_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        try:
            text = extract_conversation_from_image(screenshot_file)
            return JsonResponse({'ocr_text': text})
        except Exception as e:
            print("OCR error:", e)
            return JsonResponse({'error': 'OCR failed'}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@require_POST
def delete_conversation(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    convo_id = request.POST.get('id')
    try:
        convo = Conversation.objects.get(id=convo_id, user=request.user)
        convo.delete()
        return JsonResponse({'success': True})
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

def generate_title(last_text):
    # Find all 'her:' messages (with flexible spacing)
    matches = re.findall(r'(?:^|\n)her\s*:\s*(.+)', last_text, re.IGNORECASE)

    if matches:
        snippet = matches[-1][:40]  # use the LAST match
    else:
        snippet = last_text.strip().split('\n')[-1][:40]  # fallback to last line

    # Clean and format snippet
    snippet = re.sub(r'\s+', ' ', snippet).strip().capitalize()
    title = f"{snippet}..."

    return title
