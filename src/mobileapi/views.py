from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.db import IntegrityError
import logging

from conversation.utils.custom_gpt import generate_custom_response
from conversation.utils.image_gpt import extract_conversation_from_image
from conversation.models import ChatCredit, TrialIP
from django.utils import timezone
import ipware

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address"""
    ip_info = ipware.get_client_ip(request)
    return ip_info[0] if ip_info[0] else '127.0.0.1'

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    try:
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        
        if not all([username, email, password]):
            return HttpResponseBadRequest("Missing required fields")
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response({"success": False, "error": "Username already exists"})
        
        if User.objects.filter(email=email).exists():
            return Response({"success": False, "error": "Email already exists"})
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Get or create chat credit (should be created by signal, but ensure it exists)
        chat_credit, created = ChatCredit.objects.get_or_create(
            user=user,
            defaults={'balance': 6}  # 3 free + 3 signup bonus
        )
        
        return Response({
            "success": True,
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance
        })
        
    except IntegrityError:
        return Response({"success": False, "error": "User creation failed"})
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Registration failed"})

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Login user"""
    try:
        username = request.data.get("username")
        password = request.data.get("password")
        
        if not all([username, password]):
            return HttpResponseBadRequest("Missing username or password")
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({"success": False, "error": "Invalid credentials"})
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Get chat credits
        chat_credit, created = ChatCredit.objects.get_or_create(
            user=user,
            defaults={'balance': 10}  # Default credits for existing users
        )
        
        return Response({
            "success": True,
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Login failed"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get user profile"""
    try:
        user = request.user
        chat_credit = ChatCredit.objects.get(user=user)
        
        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance
        })
    except ChatCredit.DoesNotExist:
        # Create chat credit if doesn't exist
        chat_credit = ChatCredit.objects.create(user=user, balance=10)
        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance
        })

@api_view(["POST"])
@permission_classes([AllowAny])
def generate_text_with_credits(request):
    """Generate text with credit system"""
    try:
        last_text = request.data.get("last_text")
        situation = request.data.get("situation")
        her_info = request.data.get("her_info", "")
        
        if not last_text or not situation:
            return HttpResponseBadRequest("Missing required fields")
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check credits
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
                if chat_credit.balance <= 0:
                    return Response({
                        "success": False, 
                        "error": "insufficient_credits",
                        "message": "No credits remaining. Please upgrade your account."
                    })
                
                # Generate response
                reply, success = generate_custom_response(last_text, situation, her_info)
                
                if success:
                    # Deduct credit
                    chat_credit.balance -= 1
                    chat_credit.total_used += 1
                    chat_credit.save()
                
                return Response({
                    "success": success, 
                    "reply": reply,
                    "credits_remaining": chat_credit.balance
                })
                
            except ChatCredit.DoesNotExist:
                # Create chat credit for user
                chat_credit = ChatCredit.objects.create(user=request.user, balance=9)  # 10-1
                reply, success = generate_custom_response(last_text, situation, her_info)
                
                return Response({
                    "success": success, 
                    "reply": reply,
                    "credits_remaining": chat_credit.balance
                })
        else:
            # Handle guest users with IP-based trial
            client_ip = get_client_ip(request)
            trial_ip, created = TrialIP.objects.get_or_create(
                ip_address=client_ip,
                defaults={'trial_used': False, 'credits_used': 0}
            )
            
            # Check if guest has used all 3 trial credits
            if trial_ip.credits_used >= 3:
                return Response({
                    "success": False,
                    "error": "trial_expired",
                    "message": "Trial expired. Please sign up for more credits."
                })
            
            # Generate response
            reply, success = generate_custom_response(last_text, situation, her_info)
            
            if success:
                # Increment trial credits used
                trial_ip.credits_used += 1
                if trial_ip.credits_used >= 3:
                    trial_ip.trial_used = True
                trial_ip.save()
            
            return Response({
                "success": success, 
                "reply": reply,
                "is_trial": True,
                "trial_credits_remaining": 3 - trial_ip.credits_used
            })
            
    except Exception as e:
        logger.error(f"Generate text error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Generation failed"})

@api_view(["POST"])
@permission_classes([AllowAny])
def extract_from_image_with_credits(request):
    """Extract from image with credit system"""
    try:
        screenshot = request.FILES.get("screenshot")
        
        if not screenshot:
            return HttpResponseBadRequest("No file provided")
        
        # Validate file
        if screenshot.size == 0:
            return HttpResponseBadRequest("Empty file received")
            
        if screenshot.size > 10 * 1024 * 1024:  # 10MB limit
            return HttpResponseBadRequest("File too large (max 10MB)")
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
        if screenshot.content_type and screenshot.content_type not in allowed_types:
            logger.warning(f"Unusual content type: {screenshot.content_type}")
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
                if chat_credit.balance <= 0:
                    return Response({
                        "success": False, 
                        "error": "insufficient_credits",
                        "conversation": "No credits remaining. Please upgrade your account."
                    })
                
                # Extract conversation
                conversation = extract_conversation_from_image(screenshot)
                
                if conversation and conversation.strip():
                    # Deduct credit
                    chat_credit.balance -= 1
                    chat_credit.total_used += 1
                    chat_credit.save()
                    
                    return Response({
                        "conversation": conversation,
                        "credits_remaining": chat_credit.balance
                    })
                else:
                    return Response({
                        "conversation": "Failed to extract conversation. Please try again with a clearer screenshot."
                    })
                
            except ChatCredit.DoesNotExist:
                chat_credit = ChatCredit.objects.create(user=request.user, balance=9)  # 10-1
                conversation = extract_conversation_from_image(screenshot)
                
                return Response({
                    "conversation": conversation or "Failed to extract conversation.",
                    "credits_remaining": chat_credit.balance
                })
        else:
            # Handle guest users
            client_ip = get_client_ip(request)
            trial_ip, created = TrialIP.objects.get_or_create(
                ip_address=client_ip,
                defaults={'trial_used': False, 'credits_used': 0}
            )
            
            # Check if guest has used all 3 trial credits
            if trial_ip.credits_used >= 3:
                return Response({
                    "conversation": "Trial expired. Please sign up for more credits.",
                    "trial_expired": True
                })
            
            conversation = extract_conversation_from_image(screenshot)
            
            if conversation and conversation.strip():
                # Increment trial credits used
                trial_ip.credits_used += 1
                if trial_ip.credits_used >= 3:
                    trial_ip.trial_used = True
                trial_ip.save()
            
            return Response({
                "conversation": conversation or "Failed to extract conversation.",
                "is_trial": True,
                "trial_credits_remaining": 3 - trial_ip.credits_used
            })
            
    except Exception as e:
        logger.error(f"Image extraction error: {str(e)}", exc_info=True)
        return Response({
            "conversation": f"Error processing image: {str(e)}"
        }, status=500)