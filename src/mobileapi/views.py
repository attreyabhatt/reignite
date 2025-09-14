from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import HttpResponseBadRequest
import logging

from conversation.utils.custom_gpt import generate_custom_response
from conversation.utils.image_gpt import extract_conversation_from_image

logger = logging.getLogger(__name__)

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
    try:
        screenshot = request.FILES.get("screenshot")
        
        if not screenshot:
            logger.error("No file provided in request.FILES")
            logger.error(f"Request.FILES: {request.FILES}")
            logger.error(f"Request.POST: {request.POST}")
            return HttpResponseBadRequest("No file provided")
        
        # Log file details
        logger.info(f"Received file: {screenshot.name}")
        logger.info(f"File size: {screenshot.size} bytes")
        logger.info(f"Content type: {screenshot.content_type}")
        
        # Validate file
        if screenshot.size == 0:
            logger.error("Empty file received")
            return HttpResponseBadRequest("Empty file received")
            
        if screenshot.size > 10 * 1024 * 1024:  # 10MB limit
            logger.error(f"File too large: {screenshot.size} bytes")
            return HttpResponseBadRequest("File too large (max 10MB)")
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
        if screenshot.content_type and screenshot.content_type not in allowed_types:
            logger.warning(f"Unusual content type: {screenshot.content_type}")
        
        conversation = extract_conversation_from_image(screenshot)
        
        if not conversation or conversation.strip() == "":
            logger.error("Empty conversation extracted")
            return Response({
                "conversation": "Failed to extract conversation. Please try again with a clearer screenshot."
            })
            
        logger.info("Successfully extracted conversation")
        return Response({"conversation": conversation})
        
    except Exception as e:
        logger.error(f"Error in extract_from_image: {str(e)}", exc_info=True)
        return Response({
            "conversation": f"Error processing image: {str(e)}"
        }, status=500)