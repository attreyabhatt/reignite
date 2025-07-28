from django.shortcuts import render
from django.http import JsonResponse
import json
from conversation.utils.gpt import generate_comebacks

def home(request):
    return render(request, 'home.html')

def ajax_reply(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        last_text = data.get('last_text', '')
        comebacks = generate_comebacks(last_text)
        print(f"Generated comebacks: {comebacks}")
        return JsonResponse({
            'todd': comebacks.get("Todd Valentine", ""),
            'julien': comebacks.get("Julien Blanc", ""),
            'neil': comebacks.get("Neil Strauss", "")
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)
