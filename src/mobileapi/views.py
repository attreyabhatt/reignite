from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import HttpResponseBadRequest

from conversation.utils.custom_gpt import generate_custom_response
from conversation.utils.image_gpt import extract_conversation_from_image

@api_view(["POST"])
@permission_classes([AllowAny])
def generate_text(request):
    last_text = request.data.get("last_text")
    situation = request.data.get("situation")
    her_info = request.data.get("her_info", "")
    if not last_text or not situation:
        return HttpResponseBadRequest("Missing required fields")
    reply, success = generate_custom_response(last_text, situation, her_info)
    return Response({"success": success, "reply": reply})

@api_view(["POST"])
@permission_classes([AllowAny])
def extract_from_image(request):
    screenshot = request.FILES.get("screenshot")
    if not screenshot:
        return HttpResponseBadRequest("No file provided")
    conversation = extract_conversation_from_image(screenshot)
    return Response({"conversation": conversation})
