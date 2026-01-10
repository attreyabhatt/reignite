from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import renderers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.db import IntegrityError
import json
import logging

from conversation.utils.custom_gpt import generate_custom_response
from conversation.utils.image_gpt import extract_conversation_from_image, stream_conversation_from_image_bytes
from conversation.utils.profile_analyzer import analyze_profile_image, stream_profile_analysis_bytes
from .renderers import EventStreamRenderer
from conversation.models import ChatCredit, TrialIP
from django.utils import timezone

logger = logging.getLogger(__name__)


def _sse_event(payload):
    return f"data: {payload}\n\n"

def get_client_ip(request):
    """Get client IP address"""
    try:
        from ipware import get_client_ip as ipware_get_client_ip
        ip, is_routable = ipware_get_client_ip(request)
        return ip if ip else '127.0.0.1'
    except ImportError:
        # Fallback if ipware is not installed
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

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
        
        # Create chat credit - ALWAYS start with 3 credits for new signups
        # Don't carry over any guest trial credits
        chat_credit = ChatCredit.objects.create(
            user=user,
            balance=3,  # Fresh 3 credits for signup
            signup_bonus_given=True,
            total_earned=3
        )
        
        logger.info(f"New user created: {username} with {chat_credit.balance} credits")
        
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
        tone = request.data.get("tone", "Natural")  # Default to Natural
        
        if not last_text or not situation:
            return HttpResponseBadRequest("Missing required fields")
        
        # Map mobile situations to correct prompts
        if situation == "stuck_after_reply":
            situation = "mobile_stuck_reply_prompt"
        
        logger.info(f"Generate request - User authenticated: {request.user.is_authenticated}")
        logger.info(f"User: {request.user if request.user.is_authenticated else 'Anonymous'}")
        logger.info(f"Situation: {situation}, Tone: {tone}")
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            logger.info(f"Authenticated user: {request.user.username}")
            # Check credits
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
                logger.info(f"User credits: {chat_credit.balance}")
                
                if chat_credit.balance <= 0:
                    return Response({
                        "success": False, 
                        "error": "insufficient_credits",
                        "message": "No credits remaining. Please upgrade your account."
                    })
                
                # Generate response with tone
                reply, success = generate_custom_response(last_text, situation, her_info, tone=tone)
                
                if success:
                    # Deduct credit
                    chat_credit.balance -= 1
                    chat_credit.total_used += 1
                    chat_credit.save()
                    logger.info(f"Credit deducted. New balance: {chat_credit.balance}")
                
                return Response({
                    "success": success, 
                    "reply": reply,
                    "credits_remaining": chat_credit.balance
                })
                
            except ChatCredit.DoesNotExist:
                logger.warning(f"ChatCredit not found for user {request.user.username}, creating one")
                # Create chat credit for user
                chat_credit = ChatCredit.objects.create(user=request.user, balance=5)  # 6-1
                reply, success = generate_custom_response(last_text, situation, her_info, tone=tone)
                
                return Response({
                    "success": success, 
                    "reply": reply,
                    "credits_remaining": chat_credit.balance
                })
        else:
            logger.info("Guest user detected")
            # Handle guest users with IP-based trial
            client_ip = get_client_ip(request)
            logger.info(f"Guest IP: {client_ip}")
            
            trial_ip, created = TrialIP.objects.get_or_create(
                ip_address=client_ip,
                defaults={'trial_used': False, 'credits_used': 0}
            )
            
            logger.info(f"Trial IP - Created: {created}, Credits used: {trial_ip.credits_used}")
            
            # Check if guest has used all 3 trial credits
            if trial_ip.credits_used >= 3:
                return Response({
                    "success": False,
                    "error": "trial_expired",
                    "message": "Trial expired. Please sign up for more credits."
                })
            
            # Generate response with tone
            reply, success = generate_custom_response(last_text, situation, her_info, tone=tone)
            
            if success:
                # Increment trial credits used
                trial_ip.credits_used += 1
                if trial_ip.credits_used >= 3:
                    trial_ip.trial_used = True
                trial_ip.save()
                logger.info(f"Trial credit used. Remaining: {3 - trial_ip.credits_used}")
            
            return Response({
                "success": success, 
                "reply": reply,
                "is_trial": True,
                "trial_credits_remaining": 3 - trial_ip.credits_used
            })
            
    except Exception as e:
        logger.error(f"Generate text error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Generation failed", "message": str(e)})


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


@api_view(["POST"])
@permission_classes([AllowAny])
@renderer_classes([EventStreamRenderer, renderers.JSONRenderer])
def extract_from_image_with_credits_stream(request):
    """Stream OCR extraction with credit system"""
    screenshot = request.FILES.get("screenshot")

    if not screenshot:
        return HttpResponseBadRequest("No file provided")

    if screenshot.size == 0:
        return HttpResponseBadRequest("Empty file received")

    if screenshot.size > 10 * 1024 * 1024:
        return HttpResponseBadRequest("File too large (max 10MB)")

    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
    if screenshot.content_type and screenshot.content_type not in allowed_types:
        logger.warning(f"Unusual content type: {screenshot.content_type}")

    img_bytes = screenshot.read()

    def _error_stream(error_code, message, extra=None):
        payload = {"type": "error", "error": error_code, "message": message}
        if extra:
            payload.update(extra)
        yield _sse_event(json.dumps(payload))

    def _has_labeled_lines(text):
        lowered = text.lower()
        return any(tag in lowered for tag in ("you [", "her [", "system ["))

    if request.user.is_authenticated:
        try:
            chat_credit = ChatCredit.objects.get(user=request.user)
            if chat_credit.balance <= 0:
                return StreamingHttpResponse(
                    _error_stream("insufficient_credits", "No credits remaining. Please upgrade your account."),
                    content_type="text/event-stream",
                )
        except ChatCredit.DoesNotExist:
            chat_credit = ChatCredit.objects.create(user=request.user, balance=9)

        def gen():
            output_parts = []
            try:
                for delta in stream_conversation_from_image_bytes(img_bytes, use_resize=True):
                    output_parts.append(delta)
                    yield _sse_event(json.dumps({"type": "delta", "text": delta}))

                full = "".join(output_parts).strip()
                if not _has_labeled_lines(full):
                    yield _sse_event(json.dumps({"type": "reset"}))
                    output_parts = []
                    for delta in stream_conversation_from_image_bytes(img_bytes, use_resize=False):
                        output_parts.append(delta)
                        yield _sse_event(json.dumps({"type": "delta", "text": delta}))
                    full = "".join(output_parts).strip()

                if not full:
                    yield _sse_event(json.dumps({"type": "error", "error": "ocr_failed", "message": "Failed to extract conversation. Please try a clearer screenshot."}))
                    return

                chat_credit.balance -= 1
                chat_credit.total_used += 1
                chat_credit.save()

                yield _sse_event(
                    json.dumps(
                        {
                            "type": "done",
                            "conversation": full,
                            "credits_remaining": chat_credit.balance,
                        }
                    )
                )
            except Exception as exc:
                yield _sse_event(
                    json.dumps({"type": "error", "error": "ocr_failed", "message": str(exc)})
                )

        response = StreamingHttpResponse(gen(), content_type="text/event-stream")
    else:
        client_ip = get_client_ip(request)
        trial_ip, created = TrialIP.objects.get_or_create(
            ip_address=client_ip,
            defaults={'trial_used': False, 'credits_used': 0}
        )

        if trial_ip.credits_used >= 3:
            return StreamingHttpResponse(
                _error_stream("trial_expired", "Trial expired. Please sign up for more credits.", {"trial_expired": True}),
                content_type="text/event-stream",
            )

        def gen():
            output_parts = []
            try:
                for delta in stream_conversation_from_image_bytes(img_bytes, use_resize=True):
                    output_parts.append(delta)
                    yield _sse_event(json.dumps({"type": "delta", "text": delta}))

                full = "".join(output_parts).strip()
                if not _has_labeled_lines(full):
                    yield _sse_event(json.dumps({"type": "reset"}))
                    output_parts = []
                    for delta in stream_conversation_from_image_bytes(img_bytes, use_resize=False):
                        output_parts.append(delta)
                        yield _sse_event(json.dumps({"type": "delta", "text": delta}))
                    full = "".join(output_parts).strip()

                if full:
                    trial_ip.credits_used += 1
                    if trial_ip.credits_used >= 3:
                        trial_ip.trial_used = True
                    trial_ip.save()

                yield _sse_event(
                    json.dumps(
                        {
                            "type": "done",
                            "conversation": full or "Failed to extract conversation.",
                            "is_trial": True,
                            "trial_credits_remaining": 3 - trial_ip.credits_used
                        }
                    )
                )
            except Exception as exc:
                yield _sse_event(
                    json.dumps({"type": "error", "error": "ocr_failed", "message": str(exc)})
                )

        response = StreamingHttpResponse(gen(), content_type="text/event-stream")

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

@api_view(["POST"])
@permission_classes([AllowAny])
def analyze_profile(request):
    """Analyze profile image/screenshot to extract information"""
    try:
        profile_image = request.FILES.get("profile_image")
        
        if not profile_image:
            return HttpResponseBadRequest("No file provided")
        
        # Validate file
        if profile_image.size == 0:
            return HttpResponseBadRequest("Empty file received")
            
        if profile_image.size > 10 * 1024 * 1024:  # 10MB limit
            return HttpResponseBadRequest("File too large (max 10MB)")
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
        if profile_image.content_type and profile_image.content_type not in allowed_types:
            logger.warning(f"Unusual content type: {profile_image.content_type}")
        
        logger.info("Analyzing profile image...")
        
        # Analyze the profile image
        analysis = analyze_profile_image(profile_image)
        
        if not analysis or "Failed" in analysis or "Unable" in analysis:
            logger.error("Profile analysis failed")
            return Response({
                "success": False,
                "profile_info": "Could not analyze the image. Please try a clearer screenshot or photo."
            })
        
        logger.info("Profile analysis successful")
        return Response({
            "success": True,
            "profile_info": analysis
        })
        
    except Exception as e:
        logger.error(f"Profile analysis error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "profile_info": f"Error analyzing image: {str(e)}"
        }, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
@renderer_classes([EventStreamRenderer, renderers.JSONRenderer])
def analyze_profile_stream(request):
    """Stream profile analysis"""
    profile_image = request.FILES.get("profile_image")

    if not profile_image:
        return HttpResponseBadRequest("No file provided")

    if profile_image.size == 0:
        return HttpResponseBadRequest("Empty file received")

    if profile_image.size > 10 * 1024 * 1024:
        return HttpResponseBadRequest("File too large (max 10MB)")

    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
    if profile_image.content_type and profile_image.content_type not in allowed_types:
        logger.warning(f"Unusual content type: {profile_image.content_type}")

    img_bytes = profile_image.read()

    def gen():
        output_parts = []
        try:
            for delta in stream_profile_analysis_bytes(img_bytes):
                output_parts.append(delta)
                yield _sse_event(json.dumps({"type": "delta", "text": delta}))

            full = "".join(output_parts).strip()
            if not full or len(full) < 20:
                yield _sse_event(
                    json.dumps({"type": "error", "error": "analysis_failed", "message": "Could not analyze the image. Please try a clearer screenshot or photo."})
                )
                return

            yield _sse_event(
                json.dumps(
                    {"type": "done", "success": True, "profile_info": full}
                )
            )
        except Exception as exc:
            yield _sse_event(
                json.dumps({"type": "error", "error": "analysis_failed", "message": str(exc)})
            )

    response = StreamingHttpResponse(gen(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
