from django.shortcuts import render,redirect
from .models import Conversation, ChatCredit
from django.urls import reverse
from django.http import JsonResponse
import json
from conversation.utils.gpt import generate_comebacks
from conversation.utils.image_gpt import extract_conversation_from_image
from conversation.utils.custom_gpt import generate_custom_comeback
from conversation.utils.todd_gpt import generate_toddv_comeback
from django.utils import timezone
from django.views.decorators.http import require_POST

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
        girl_title = data.get('girl_title', '').strip()
        last_text = data.get('last_text', '').strip()
        platform = data.get('platform', '').strip()
        what_happened = data.get('what_happened', '').strip()
        print(last_text)
        # Save the conversation for the user
        conversation, created = Conversation.objects.get_or_create(
            user=request.user,
            girl_title=girl_title,
            defaults={
                'content': last_text,
                'platform': platform,
                'what_happened': what_happened,
            }
        )
        if not created:
            conversation.content = last_text
            conversation.platform = platform
            conversation.what_happened = what_happened
            conversation.save()


        # Deduct one credit
        chat_credit.balance -= 1
        chat_credit.save()  # last_updated auto-updates

        # Generate your AI response (dummy below)
        # comebacks = generate_comebacks(last_text)
        # todd_comeback = generate_toddv_comeback(last_text,platform,what_happened).strip('"')
        custom_response = generate_custom_comeback(last_text,platform,what_happened)
        response_data = {
        'custom': custom_response,
        'credits_left': chat_credit.balance,
        }
        # response_data = {
        #     'alex': comebacks.get("AlexTextGameCoach", ""),
        #     'custom': custom_comeback,
        #     'toddv' : todd_comeback,
        #     'credits_left': chat_credit.balance,
        # }
        
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
            'platform': convo.platform,
            'what_happened': convo.what_happened,
        })
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    
from django.views.decorators.csrf import csrf_exempt  # Or use @csrf_protect if you use AJAX CSRF header

@csrf_exempt  # Remove this and use CSRF token if your AJAX includes it
def ocr_screenshot(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            if 'screenshot_credits' not in request.session:
                    request.session['screenshot_credits'] = 5
            
            # Deduct one screenshot credit session
            request.session['screenshot_credits'] = request.session['screenshot_credits'] - 1
            screenshot_credits_credits_left = request.session['screenshot_credits']
            if screenshot_credits_credits_left <= 0:
                return JsonResponse({'error': 'Limit reached. Please signup to upload more screenshots'}, status=401)
            
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


