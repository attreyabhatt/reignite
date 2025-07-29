from django.shortcuts import render
from django.http import JsonResponse
import json
from conversation.utils.gpt import generate_comebacks

def home(request):
    return render(request, 'home.html')

def ajax_reply(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        last_text = data.get('last-reply', '').strip()
        
        comebacks = generate_comebacks(last_text)
        return JsonResponse({
            'alex': comebacks.get("AlexTextGameCoach", ""),
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)
