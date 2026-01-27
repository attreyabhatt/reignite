from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import renderers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from allauth.account.forms import ResetPasswordForm
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from decimal import Decimal, InvalidOperation
import random
import json
import logging
from functools import lru_cache
from datetime import datetime, timedelta, timezone as dt_timezone

from conversation.utils.custom_gpt import generate_custom_response, generate_openers_from_image
from conversation.utils.mobile.custom_mobile import generate_mobile_response, generate_mobile_openers_from_image
from conversation.utils.mobile.image_mobile import extract_conversation_from_image_mobile
from conversation.utils.image_gpt import extract_conversation_from_image, stream_conversation_from_image_bytes
from conversation.utils.profile_analyzer import analyze_profile_image, stream_profile_analysis_bytes
from .renderers import EventStreamRenderer
from conversation.models import ChatCredit, TrialIP, GuestTrial, RecommendedOpener
from reignitehome.models import ContactMessage
from pricing.models import CreditPurchase
from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.utils import timezone

logger = logging.getLogger(__name__)

# Mobile subscription/fair-use limits
SUBSCRIPTION_WEEKLY_LIMIT = 400  # fair-use cap for subscribers

def _mask_token(token):
    if not token:
        return ""
    if len(token) <= 12:
        return f"{token[:4]}...{token[-4:]}"
    return f"{token[:8]}...{token[-4:]}"


def _sse_event(payload):
    return f"data: {payload}\n\n"

@lru_cache(maxsize=1)
def _get_google_play_client():
    service_account_content = settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON_CONTENT
    service_account_path = settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
    creds = None

    if service_account_content:
        try:
            info = json.loads(service_account_content)
            creds = Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/androidpublisher"],
            )
        except json.JSONDecodeError:
            logger.error("Invalid GOOGLE_PLAY_SERVICE_ACCOUNT_JSON_CONTENT")
            return None
    elif service_account_path:
        creds = Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/androidpublisher"],
        )
    else:
        logger.error("Google Play client not configured: missing service account settings")
        return None

    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)

def _verify_google_play_purchase(product_id, purchase_token):
    client = _get_google_play_client()
    if client is None:
        return False, "google_play_not_configured"

    try:
        response = (
            client.purchases()
            .products()
            .get(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                productId=product_id,
                token=purchase_token,
            )
            .execute()
        )
    except HttpError as exc:
        logger.warning("Google Play verification failed: %s", exc)
        return False, "google_play_verification_failed"

    purchase_state = response.get("purchaseState")
    if purchase_state != 0:
        return False, "google_play_not_purchased"

    return True, None

def _acknowledge_google_play_purchase(product_id, purchase_token):
    """Acknowledge/consume a Google Play purchase to unlock the SKU."""
    client = _get_google_play_client()
    if client is None:
        logger.error("Google Play client not configured")
        return False, "google_play_not_configured"

    try:
        # First, check if purchase exists and is valid
        purchase_info = (
            client.purchases()
            .products()
            .get(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                productId=product_id,
                token=purchase_token,
            )
            .execute()
        )

        logger.info(
            "Google Play purchase info: product_id=%s acknowledgementState=%s consumptionState=%s",
            product_id,
            purchase_info.get("acknowledgementState"),
            purchase_info.get("consumptionState"),
        )

        # Acknowledge the purchase (for non-consumables and subscriptions)
        # acknowledgementState: 0 = not acknowledged, 1 = acknowledged
        if purchase_info.get("acknowledgementState") == 0:
            try:
                client.purchases().products().acknowledge(
                    packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                    productId=product_id,
                    token=purchase_token,
                ).execute()
                logger.info("Acknowledged Google Play purchase: product_id=%s", product_id)
            except HttpError as ack_exc:
                # Acknowledgement might fail if already acknowledged, which is fine
                logger.warning("Failed to acknowledge purchase (might already be acknowledged): %s", ack_exc)

        # Consume the purchase (for consumables) - this is what unlocks the SKU for repurchase
        # consumptionState: 0 = not consumed, 1 = consumed
        try:
            client.purchases().products().consume(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                productId=product_id,
                token=purchase_token,
            ).execute()
            logger.info("Consumed Google Play purchase: product_id=%s token=%s", product_id, purchase_token[:20])
            return True, None
        except HttpError as consume_exc:
            # If consumption fails, it might already be consumed
            logger.warning("Failed to consume purchase: %s", consume_exc)
            # Still return success if acknowledgement worked
            return True, None

    except HttpError as exc:
        logger.error("Failed to acknowledge/consume Google Play purchase: %s", exc)
        return False, str(exc)
    except Exception as exc:
        logger.error("Unexpected error acknowledging purchase: %s", exc, exc_info=True)
        return False, str(exc)


def _reset_weekly_counter(chat_credit):
    now = timezone.now()
    reset_at = chat_credit.subscriber_weekly_reset_at
    if not reset_at or (now - reset_at).days >= 7:
        chat_credit.subscriber_weekly_actions = 0
        chat_credit.subscriber_weekly_reset_at = now
        chat_credit.save(update_fields=["subscriber_weekly_actions", "subscriber_weekly_reset_at"])


def _is_subscription_active(chat_credit):
    """Check if a stored subscription is active and not expired."""
    if not chat_credit.is_subscribed:
        return False
    if chat_credit.subscription_expiry and chat_credit.subscription_expiry < timezone.now():
        chat_credit.is_subscribed = False
        chat_credit.subscription_auto_renewing = False
        chat_credit.subscription_purchase_token = None
        chat_credit.subscription_product_id = None
        chat_credit.subscription_platform = None
        chat_credit.save(update_fields=[
            "is_subscribed",
            "subscription_auto_renewing",
            "subscription_purchase_token",
            "subscription_product_id",
            "subscription_platform",
        ])
        return False
    return True


def _ensure_subscriber_allowance(chat_credit):
    """Enforce weekly fair-use cap for subscribers. Returns (allowed, remaining)."""
    _reset_weekly_counter(chat_credit)
    if chat_credit.subscriber_weekly_actions >= SUBSCRIPTION_WEEKLY_LIMIT:
        return False, 0
    chat_credit.subscriber_weekly_actions += 1
    chat_credit.save(update_fields=["subscriber_weekly_actions"])
    remaining = max(0, SUBSCRIPTION_WEEKLY_LIMIT - chat_credit.subscriber_weekly_actions)
    return True, remaining


def _subscription_payload(chat_credit):
    """Return subscription info payload for mobile clients."""
    expiry = chat_credit.subscription_expiry.isoformat() if chat_credit.subscription_expiry else None
    return {
        "is_subscribed": _is_subscription_active(chat_credit),
        "subscription_expiry": expiry,
        "subscription_product_id": chat_credit.subscription_product_id,
        "subscription_platform": chat_credit.subscription_platform,
        "subscription_auto_renewing": chat_credit.subscription_auto_renewing,
        "subscriber_weekly_remaining": max(
            0,
            SUBSCRIPTION_WEEKLY_LIMIT - (chat_credit.subscriber_weekly_actions or 0)
        ),
        "subscriber_weekly_limit": SUBSCRIPTION_WEEKLY_LIMIT,
    }


def _reset_trial_if_stale(trial_ip):
    """Reset guest trial if more than a day old to avoid stale lockouts."""
    now = timezone.now()
    if trial_ip.first_seen and (now - trial_ip.first_seen) >= timedelta(days=1):
        trial_ip.credits_used = 0
        trial_ip.trial_used = False
        trial_ip.first_seen = now
        trial_ip.save(update_fields=["credits_used", "trial_used", "first_seen"])


def _get_guest_id(request):
    return (request.META.get("HTTP_X_GUEST_ID") or "").strip()


def _get_or_create_guest_trial(request):
    guest_id = _get_guest_id(request)
    client_ip = get_client_ip(request)
    if guest_id:
        guest_trial, created = GuestTrial.objects.get_or_create(
            guest_id=guest_id,
            defaults={"ip_address": client_ip, "credits_used": 0, "trial_used": False},
        )
        if guest_trial.ip_address != client_ip:
            guest_trial.ip_address = client_ip
            guest_trial.save(update_fields=["ip_address", "last_seen"])
        return guest_trial, created, guest_id, client_ip

    # Fallback for older clients without guest id
    trial_ip, created = TrialIP.objects.get_or_create(
        ip_address=client_ip,
        defaults={'trial_used': False, 'credits_used': 0}
    )
    return trial_ip, created, "", client_ip


def _select_recommended_openers(count):
    qs = list(RecommendedOpener.objects.filter(is_active=True).order_by("sort_order", "id"))
    if not qs:
        return []
    if count is None or count <= 0:
        return qs
    if len(qs) <= count:
        return qs
    return random.sample(qs, count)


def _verify_google_play_subscription(product_id, purchase_token):
    client = _get_google_play_client()
    if client is None:
        logger.error(
            "Google Play verify subscription aborted: client not configured product_id=%s token=%s package=%s",
            product_id,
            _mask_token(purchase_token),
            getattr(settings, "GOOGLE_PLAY_PACKAGE_NAME", None),
        )
        return False, "google_play_not_configured", None

    try:
        logger.info(
            "Google Play verify subscription start product_id=%s token=%s package=%s",
            product_id,
            _mask_token(purchase_token),
            settings.GOOGLE_PLAY_PACKAGE_NAME,
        )
        resp = (
            client.purchases()
            .subscriptions()
            .get(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                subscriptionId=product_id,
                token=purchase_token,
            )
            .execute()
        )
        logger.info("Play subscription response: %s", resp)

        purchase_state = resp.get("purchaseState")
        if purchase_state not in (0, None):
            return False, "google_play_not_purchased", None

        expiry_ms = resp.get("expiryTimeMillis")
        expiry_dt = None
        if expiry_ms:
            expiry_dt = datetime.fromtimestamp(int(expiry_ms) / 1000.0, tz=dt_timezone.utc)

        return True, None, {
            "expiry": expiry_dt,
            "auto_renewing": resp.get("autoRenewing", False),
            "kind": resp.get("kind"),
        }
    except HttpError as exc:
        logger.warning(
            "Google Play subscription verification failed product_id=%s token=%s package=%s status=%s content=%s error=%s",
            product_id,
            _mask_token(purchase_token),
            settings.GOOGLE_PLAY_PACKAGE_NAME,
            getattr(exc, "status_code", None),
            getattr(exc, "content", None),
            exc,
        )
        return False, "google_play_verification_failed", None
    except Exception as exc:
        logger.error("Unexpected Play subscription verification error: %s", exc, exc_info=True)
        return False, "verification_failed", None

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
        
        # Ensure chat credits exist (signal may already create them)
        chat_credit, created = ChatCredit.objects.get_or_create(
            user=user,
            defaults={
                "balance": 3,
                "signup_bonus_given": True,
                "total_earned": 3,
            },
        )
        
        logger.info(f"New user created: {username} with {chat_credit.balance} credits")
        
        subscription_info = _subscription_payload(chat_credit)

        return Response({
            "success": True,
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance,
            **subscription_info,
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

        subscription_info = _subscription_payload(chat_credit)
        
        return Response({
            "success": True,
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance,
            **subscription_info,
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Login failed"})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def google_play_purchase(request):
    """Record a Google Play purchase and grant credits."""
    try:
        product_id = (request.data.get("product_id") or "").strip()
        purchase_token = (request.data.get("purchase_token") or "").strip()
        order_id = (request.data.get("order_id") or "").strip()
        price = request.data.get("price")
        currency = (request.data.get("currency") or "").strip()

        if not product_id or not purchase_token:
            logger.warning(
                "GP purchase missing fields user=%s product_id=%s order_id=%s",
                getattr(request.user, "username", "anon"),
                product_id,
                order_id,
            )
            return Response(
                {"success": False, "error": "Missing product_id or purchase_token"},
                status=400,
            )

        credit_map = {
            "starter_pack_v1": 25,
            "pro_pack_v1": 75,
            "ultimate_pack_v1": 200,
        }
        credits = credit_map.get(product_id)
        if not credits:
            logger.warning(
                "GP purchase unknown product user=%s product_id=%s",
                getattr(request.user, "username", "anon"),
                product_id,
            )
            return Response(
                {"success": False, "error": "Unknown product_id"},
                status=400,
            )

        is_valid, verify_error = _verify_google_play_purchase(
            product_id,
            purchase_token,
        )
        if not is_valid:
            logger.warning(
                "GP verify failed user=%s product_id=%s token=%s error=%s",
                getattr(request.user, "username", "anon"),
                product_id,
                purchase_token,
                verify_error,
            )

            # CRITICAL: Even if verification fails (refunded/cancelled), try to consume it
            # This removes it from the purchase queue so it stops appearing in restorePurchases()
            if verify_error == "google_play_not_purchased":
                logger.info("Attempting to consume refunded/cancelled purchase to clear queue: token=%s", purchase_token[:20])
                ack_success, ack_error = _acknowledge_google_play_purchase(product_id, purchase_token)
                if ack_success:
                    logger.info("Successfully consumed old purchase from queue: token=%s", purchase_token[:20])
                else:
                    logger.warning("Failed to consume old purchase: error=%s", ack_error)

            return Response(
                {"success": False, "error": verify_error or "verification_failed"},
                status=400,
            )

        existing = CreditPurchase.objects.filter(
            transaction_id=purchase_token,
            payment_provider="google_play",
        ).first()
        if existing:
            chat_credit, _ = ChatCredit.objects.get_or_create(user=request.user)
            logger.info(
                "GP purchase already processed user=%s product_id=%s token=%s balance=%s",
                request.user.username,
                product_id,
                purchase_token,
                chat_credit.balance,
            )
            # CRITICAL: Acknowledge/consume the purchase even if already processed
            # This ensures the SKU is unlocked for future purchases
            ack_success, ack_error = _acknowledge_google_play_purchase(product_id, purchase_token)
            if not ack_success:
                logger.warning(
                    "Failed to acknowledge already-processed purchase: user=%s error=%s",
                    request.user.username,
                    ack_error,
                )
            return Response(
                {"success": True, "credits_remaining": chat_credit.balance}
            )

        amount_paid = Decimal("0.00")
        if price is not None:
            try:
                amount_paid = Decimal(str(price))
            except (InvalidOperation, TypeError):
                amount_paid = Decimal("0.00")

        chat_credit, _ = ChatCredit.objects.get_or_create(user=request.user)
        chat_credit.add_credits(credits, reason="google_play_purchase")

        CreditPurchase.objects.create(
            user=request.user,
            credits_purchased=credits,
            amount_paid=amount_paid,
            transaction_id=purchase_token,
            payment_status="COMPLETED",
            payment_provider="google_play",
        )

        logger.info(
            "Google Play purchase recorded user=%s product_id=%s order_id=%s token=%s currency=%s credits_added=%s balance=%s",
            request.user.username,
            product_id,
            order_id or "none",
            purchase_token,
            currency or "unknown",
            credits,
            chat_credit.balance,
        )

        # CRITICAL: Acknowledge/consume the purchase with Google Play
        # This unlocks the SKU so it can be repurchased (for consumables)
        ack_success, ack_error = _acknowledge_google_play_purchase(product_id, purchase_token)
        if not ack_success:
            logger.error(
                "Failed to acknowledge new purchase: user=%s product_id=%s error=%s",
                request.user.username,
                product_id,
                ack_error,
            )
            # Don't fail the purchase - credits were already granted
            # Just log the error so we can investigate

        return Response(
            {
                "success": True,
                "credits_added": credits,
                "credits_remaining": chat_credit.balance,
            }
        )
    except Exception as exc:
        logger.error(
            "Google Play purchase error user=%s product_id=%s token=%s order_id=%s",
            getattr(request.user, "username", "anon"),
            request.data.get("product_id"),
            request.data.get("purchase_token"),
            request.data.get("order_id"),
            exc_info=True,
        )
        return Response(
            {"success": False, "error": "purchase_failed"},
            status=500,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_subscription(request):
    """Verify a Google Play subscription for mobile and store subscription state."""
    product_id = (request.data.get("product_id") or "").strip()
    purchase_token = (request.data.get("purchase_token") or "").strip()

    if not product_id or not purchase_token:
        return Response(
            {"success": False, "error": "missing_fields"},
            status=400,
        )

    try:
        chat_credit, _ = ChatCredit.objects.get_or_create(user=request.user)
        logger.info(
            "Verify subscription request user=%s product_id=%s token=%s package=%s",
            request.user.username,
            product_id,
            _mask_token(purchase_token),
            getattr(settings, "GOOGLE_PLAY_PACKAGE_NAME", None),
        )
        ok, error_code, meta = _verify_google_play_subscription(product_id, purchase_token)
        now = timezone.now()

        if ok and meta:
            logger.info(
                "Verify subscription success user=%s product_id=%s expiry=%s auto_renewing=%s",
                request.user.username,
                product_id,
                meta.get("expiry"),
                meta.get("auto_renewing", False),
            )
            chat_credit.is_subscribed = True
            chat_credit.subscription_product_id = product_id
            chat_credit.subscription_platform = "google_play"
            chat_credit.subscription_purchase_token = purchase_token
            chat_credit.subscription_expiry = meta.get("expiry")
            chat_credit.subscription_auto_renewing = meta.get("auto_renewing", False)
            chat_credit.subscription_last_checked = now
            chat_credit.save(update_fields=[
                "is_subscribed",
                "subscription_product_id",
                "subscription_platform",
                "subscription_purchase_token",
                "subscription_expiry",
                "subscription_auto_renewing",
                "subscription_last_checked",
            ])
            payload = _subscription_payload(chat_credit)
            return Response({"success": True, **payload})

        # mark as not subscribed if verification failed
        logger.warning(
            "Verify subscription failed user=%s product_id=%s token=%s error=%s",
            request.user.username,
            product_id,
            _mask_token(purchase_token),
            error_code,
        )
        chat_credit.is_subscribed = False
        chat_credit.subscription_auto_renewing = False
        chat_credit.subscription_platform = "google_play"
        chat_credit.subscription_last_checked = now
        chat_credit.save(update_fields=[
            "is_subscribed",
            "subscription_auto_renewing",
            "subscription_platform",
            "subscription_last_checked",
        ])
        return Response(
            {"success": False, "error": error_code or "verification_failed"},
            status=400,
        )
    except Exception as exc:
        logger.error("Subscription verification error: %s", exc, exc_info=True)
        return Response(
            {"success": False, "error": "verification_failed"},
            status=500,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """Get the user's payment/purchase history."""
    try:
        purchases = CreditPurchase.objects.filter(user=request.user).order_by('-timestamp')[:50]

        history = []
        for purchase in purchases:
            history.append({
                "id": purchase.id,
                "credits_purchased": purchase.credits_purchased,
                "amount_paid": str(purchase.amount_paid),
                "timestamp": purchase.timestamp.isoformat(),
                "transaction_id": purchase.transaction_id or "",
                "payment_status": purchase.payment_status,
                "payment_provider": purchase.payment_provider or "",
            })

        return Response({
            "success": True,
            "purchases": history,
        })
    except Exception as exc:
        logger.error("Payment history error user=%s", request.user.username, exc_info=True)
        return Response(
            {"success": False, "error": "Failed to fetch payment history"},
            status=500,
        )

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request):
    """Send password reset email without exposing account existence."""
    django_request = getattr(request, "_request", request)
    email = (request.data.get("email") or "").strip()

    if not email:
        return Response({"success": False, "error": "Email is required"}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return Response({"success": False, "error": "Invalid email address"}, status=400)

    form = ResetPasswordForm(data={"email": email})
    if form.is_valid():
        setattr(django_request, "is_mobile_password_reset", True)
        form.save(django_request)

    return Response(
        {
            "success": True,
            "message": "If an account exists for that email, a reset link was sent.",
        }
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get user profile"""
    try:
        user = request.user
        chat_credit = ChatCredit.objects.get(user=user)
        subscription_info = _subscription_payload(chat_credit)
        
        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance,
            **subscription_info,
        })
    except ChatCredit.DoesNotExist:
        # Create chat credit if doesn't exist
        chat_credit = ChatCredit.objects.create(user=user, balance=10)
        subscription_info = _subscription_payload(chat_credit)
        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "chat_credits": chat_credit.balance,
            **subscription_info,
        })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change password for logged-in user."""
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    if not current_password or not new_password:
        return Response(
            {"success": False, "error": "Missing current or new password"},
            status=400,
        )

    user = request.user
    if not user.check_password(current_password):
        return Response(
            {"success": False, "error": "Current password is incorrect"},
            status=400,
        )

    try:
        password_validation.validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        return Response(
            {"success": False, "error": " ".join(exc.messages)},
            status=400,
        )

    user.set_password(new_password)
    user.save()

    return Response({"success": True})

@api_view(["POST"])
@permission_classes([AllowAny])
def generate_text_with_credits(request):
    """Generate text with credit system"""
    try:
        auth_header_present = bool(request.META.get("HTTP_AUTHORIZATION"))
        print(
            f"[MOBILE] generate_text_with_credits path={request.path} "
            f"auth_header={auth_header_present} is_authenticated={request.user.is_authenticated} "
            f"user={getattr(request.user, 'username', 'guest')}"
        )
        last_text = request.data.get("last_text")
        situation = request.data.get("situation")
        her_info = request.data.get("her_info", "")
        tone = request.data.get("tone", "Natural")  # Default to Natural
        custom_instructions = request.data.get("custom_instructions", "")

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
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
                logger.info(f"User credits: {chat_credit.balance}")

                # Safety: ensure every non-subscriber gets at least 3 free generations total
                if not _is_subscription_active(chat_credit) and chat_credit.total_used < 3 and chat_credit.balance <= 0:
                    top_up = 3 - chat_credit.total_used
                    chat_credit.balance += top_up
                    chat_credit.total_earned += top_up
                    chat_credit.save(update_fields=["balance", "total_earned"])

                # Subscription path
                if _is_subscription_active(chat_credit):
                    allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                    if not allowed:
                        return Response(
                            {
                                "success": False,
                                "error": "fair_use_exceeded",
                                "message": "You hit the weekly fair-use limit. Try again soon.",
                                **_subscription_payload(chat_credit),
                            },
                            status=429,
                        )

                    reply, success = generate_mobile_response(
                        last_text, situation, her_info, tone=tone, custom_instructions=custom_instructions
                    )

                    return Response({
                        "success": success,
                        "reply": reply,
                        **_subscription_payload(chat_credit),
                    })

                # Non-subscribed fallback: use remaining credits as free actions
                if chat_credit.balance <= 0:
                    return Response({
                        "success": False,
                        "error": "subscription_required",
                        "message": "No credits remaining. Start your subscription to continue.",
                        **_subscription_payload(chat_credit),
                    })
                
                # Generate response with tone and custom instructions
                reply, success = generate_mobile_response(
                    last_text, situation, her_info, tone=tone, custom_instructions=custom_instructions
                )

                if success:
                    # Deduct credit (legacy/free actions)
                    chat_credit.balance -= 1
                    chat_credit.total_used += 1
                    chat_credit.save()
                    logger.info(f"Credit deducted. New balance: {chat_credit.balance}")

                return Response({
                    "success": success,
                    "reply": reply,
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })

            except ChatCredit.DoesNotExist:
                logger.warning(f"ChatCredit not found for user {request.user.username}, creating one")
                # Create chat credit for user
                chat_credit = ChatCredit.objects.create(user=request.user, balance=5)  # 6-1
                reply, success = generate_mobile_response(last_text, situation, her_info, tone=tone, custom_instructions=custom_instructions)
                
                return Response({
                    "success": success, 
                    "reply": reply,
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })
        else:
            logger.info("Guest user detected")
            # Handle guest users with IP-based trial
            trial_ip, created, guest_id, client_ip = _get_or_create_guest_trial(request)
            logger.info(f"Guest IP: {client_ip} guest_id={guest_id}")
            _reset_trial_if_stale(trial_ip)
            print(f"[MOBILE] guest Trial created={created} guest_id={guest_id} ip={client_ip} credits_used={trial_ip.credits_used}")
            
            # Check if guest has used all 3 trial credits
            if trial_ip.credits_used >= 3:
                print(f"[MOBILE] guest trial_expired guest_id={guest_id} ip={client_ip} credits_used={trial_ip.credits_used}")
                return Response({
                    "success": False,
                    "error": "trial_expired",
                    "message": "Trial expired. Please sign up for more credits."
                })
            
            # Generate response with tone and custom instructions
            reply, success = generate_mobile_response(last_text, situation, her_info, tone=tone, custom_instructions=custom_instructions)

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
        auth_header_present = bool(request.META.get("HTTP_AUTHORIZATION"))
        print(
            f"[MOBILE] extract_from_image_with_credits path={request.path} "
            f"auth_header={auth_header_present} is_authenticated={request.user.is_authenticated} "
            f"user={getattr(request.user, 'username', 'guest')}"
        )
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
                if _is_subscription_active(chat_credit):
                    allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                    if not allowed:
                        return Response(
                            {
                                "success": False,
                                "error": "fair_use_exceeded",
                                "conversation": "You hit the weekly fair-use limit. Try again soon.",
                                **_subscription_payload(chat_credit),
                            },
                            status=429,
                        )
                # For non-subscribers, OCR is free (do not check or deduct credits)

                conversation = extract_conversation_from_image_mobile(screenshot)

                return Response({
                    "conversation": conversation,
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })

            except ChatCredit.DoesNotExist:
                chat_credit = ChatCredit.objects.create(user=request.user, balance=9)  # legacy field retained
                conversation = extract_conversation_from_image_mobile(screenshot)
                
                return Response({
                    "conversation": conversation or "Failed to extract conversation.",
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })
        else:
            # Guests: OCR is free and does not consume trial credits
            conversation = extract_conversation_from_image_mobile(screenshot)
            return Response({
                "conversation": conversation or "Failed to extract conversation.",
                "is_trial": True,
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
            is_sub_active = _is_subscription_active(chat_credit)
            if is_sub_active:
                allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                if not allowed:
                    return StreamingHttpResponse(
                        _error_stream("fair_use_exceeded", "You hit the weekly fair-use limit. Try again soon.", _subscription_payload(chat_credit)),
                        content_type="text/event-stream",
                    )
            # For non-subscribers, OCR streaming is free (no credit gate)
        except ChatCredit.DoesNotExist:
            chat_credit = ChatCredit.objects.create(user=request.user, balance=9)
            is_sub_active = _is_subscription_active(chat_credit)

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

                yield _sse_event(
                    json.dumps(
                        {
                            "type": "done",
                            "conversation": full,
                            "credits_remaining": chat_credit.balance,
                            **_subscription_payload(chat_credit),
                        }
                    )
                )
            except Exception as exc:
                yield _sse_event(
                    json.dumps({"type": "error", "error": "ocr_failed", "message": str(exc)})
                )

        response = StreamingHttpResponse(gen(), content_type="text/event-stream")
    else:
        # Guests: OCR streaming is free and does not consume trial credits
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

                yield _sse_event(
                    json.dumps(
                        {
                            "type": "done",
                            "conversation": full or "Failed to extract conversation.",
                            "is_trial": True,
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
        chat_credit = None
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
        # Apply subscription/fair-use gating for authenticated users
        if request.user.is_authenticated:
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
            except ChatCredit.DoesNotExist:
                chat_credit = ChatCredit.objects.create(user=request.user, balance=5)

            if _is_subscription_active(chat_credit):
                allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                if not allowed:
                    return Response({
                        "success": False,
                        "error": "fair_use_exceeded",
                        "profile_info": "You hit the weekly fair-use limit. Try again soon.",
                        **_subscription_payload(chat_credit),
                    }, status=429)
            elif chat_credit.balance <= 0:
                return Response({
                    "success": False,
                    "error": "subscription_required",
                    "profile_info": "Start your subscription to continue.",
                    **_subscription_payload(chat_credit),
                })

        # Analyze the profile image
        analysis = analyze_profile_image(profile_image)
        
        if not analysis or "Failed" in analysis or "Unable" in analysis:
            logger.error("Profile analysis failed")
            return Response({
                "success": False,
                "profile_info": "Could not analyze the image. Please try a clearer screenshot or photo."
            })

        if request.user.is_authenticated:
            if chat_credit is None:
                chat_credit, _ = ChatCredit.objects.get_or_create(user=request.user)
            if not _is_subscription_active(chat_credit) and chat_credit.balance > 0:
                chat_credit.balance -= 1
                chat_credit.total_used += 1
                chat_credit.save()
        
        logger.info("Profile analysis successful")
        return Response({
            "success": True,
            "profile_info": analysis,
            **(_subscription_payload(ChatCredit.objects.get(user=request.user)) if request.user.is_authenticated else {}),
        })
        
    except Exception as e:
        logger.error(f"Profile analysis error: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "profile_info": f"Error analyzing image: {str(e)}"
        }, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def report_issue(request):
    """Store a support/report request from the mobile app."""
    reason = (request.data.get("reason") or "").strip()
    title = (request.data.get("title") or "").strip()
    subject = (request.data.get("subject") or "").strip()
    email = (request.data.get("email") or "").strip()

    if not all([reason, title, subject, email]):
        return Response(
            {"success": False, "error": "Missing required fields"},
            status=400,
        )

    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"success": False, "error": "Invalid email address"},
            status=400,
        )

    allowed_reasons = {choice[0] for choice in ContactMessage.REASON_CHOICES}
    if reason not in allowed_reasons:
        return Response(
            {"success": False, "error": "Invalid reason"},
            status=400,
        )

    ContactMessage.objects.create(
        reason=reason,
        title=title,
        subject=subject,
        email=email,
    )

    return Response({"success": True})


@api_view(["POST"])
@permission_classes([AllowAny])
@renderer_classes([EventStreamRenderer, renderers.JSONRenderer])
def analyze_profile_stream(request):
    """Stream profile analysis"""
    chat_credit = None
    is_sub_active = False
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

    if request.user.is_authenticated:
        try:
            chat_credit = ChatCredit.objects.get(user=request.user)
            is_sub_active = _is_subscription_active(chat_credit)
            if is_sub_active:
                allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                if not allowed:
                    return StreamingHttpResponse(
                        _error_stream("fair_use_exceeded", "You hit the weekly fair-use limit. Try again soon.", _subscription_payload(chat_credit)),
                        content_type="text/event-stream",
                    )
            elif chat_credit.balance <= 0:
                return StreamingHttpResponse(
                    _error_stream("subscription_required", "No credits remaining. Start your subscription to continue.", _subscription_payload(chat_credit)),
                    content_type="text/event-stream",
                )
        except ChatCredit.DoesNotExist:
            chat_credit = ChatCredit.objects.create(user=request.user, balance=9)
            is_sub_active = _is_subscription_active(chat_credit)

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

            if request.user.is_authenticated and chat_credit and not is_sub_active and chat_credit.balance > 0:
                chat_credit.balance -= 1
                chat_credit.total_used += 1
                chat_credit.save()

            yield _sse_event(
                json.dumps(
                    {"type": "done", "success": True, "profile_info": full, **(_subscription_payload(chat_credit) if chat_credit else {})}
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


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_openers_from_profile_image(request):
    """Generate opener messages directly from a profile image (no extraction step)."""
    try:
        auth_header_present = bool(request.META.get("HTTP_AUTHORIZATION"))
        print(
            f"[MOBILE] generate_openers_from_profile_image path={request.path} "
            f"auth_header={auth_header_present} is_authenticated={request.user.is_authenticated} "
            f"user={getattr(request.user, 'username', 'guest')}"
        )
        profile_image = request.FILES.get("profile_image")
        custom_instructions = (request.data.get("custom_instructions") or "").strip()

        if not profile_image:
            return HttpResponseBadRequest("No file provided")

        if profile_image.size == 0:
            return HttpResponseBadRequest("Empty file received")

        if profile_image.size > 10 * 1024 * 1024:  # 10MB limit
            return HttpResponseBadRequest("File too large (max 10MB)")

        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
        if profile_image.content_type and profile_image.content_type not in allowed_types:
            logger.warning(f"Unusual content type: {profile_image.content_type}")

        logger.info(f"Generating openers from image - User authenticated: {request.user.is_authenticated}")

        # Read image bytes
        img_bytes = profile_image.read()

        # Check credits
        if request.user.is_authenticated:
            logger.info(f"Authenticated user: {request.user.username}")
            try:
                chat_credit = ChatCredit.objects.get(user=request.user)
                logger.info(f"User credits: {chat_credit.balance}")

                # Safety: ensure every non-subscriber gets at least 3 free generations total
                if not _is_subscription_active(chat_credit) and chat_credit.total_used < 3 and chat_credit.balance <= 0:
                    top_up = 3 - chat_credit.total_used
                    chat_credit.balance += top_up
                    chat_credit.total_earned += top_up
                    chat_credit.save(update_fields=["balance", "total_earned"])

                if _is_subscription_active(chat_credit):
                    allowed, remaining = _ensure_subscriber_allowance(chat_credit)
                    if not allowed:
                        return Response({
                            "success": False,
                            "error": "fair_use_exceeded",
                            "message": "You hit the weekly fair-use limit. Try again soon.",
                            **_subscription_payload(chat_credit),
                        }, status=429)
                elif chat_credit.balance <= 0:
                    return Response({
                        "success": False,
                        "error": "subscription_required",
                        "message": "No credits remaining. Start your subscription to continue.",
                        **_subscription_payload(chat_credit),
                    })

                # Generate openers from image
                reply, success = generate_mobile_openers_from_image(img_bytes, custom_instructions=custom_instructions)

                if success and not _is_subscription_active(chat_credit):
                    chat_credit.balance -= 1
                    chat_credit.total_used += 1
                    chat_credit.save()
                    logger.info(f"Credit deducted. New balance: {chat_credit.balance}")

                return Response({
                    "success": success,
                    "reply": reply,
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })

            except ChatCredit.DoesNotExist:
                logger.warning(f"ChatCredit not found for user {request.user.username}, creating one")
                chat_credit = ChatCredit.objects.create(user=request.user, balance=5)
                reply, success = generate_mobile_openers_from_image(img_bytes, custom_instructions=custom_instructions)

                return Response({
                    "success": success,
                    "reply": reply,
                    "credits_remaining": chat_credit.balance,
                    **_subscription_payload(chat_credit),
                })
        else:
            logger.info("Guest user detected")
            trial_ip, created, guest_id, client_ip = _get_or_create_guest_trial(request)
            logger.info(f"Guest IP: {client_ip} guest_id={guest_id}")
            _reset_trial_if_stale(trial_ip)

            print(
                f"[MOBILE] guest Trial created={created} guest_id={guest_id} "
                f"ip={client_ip} credits_used={trial_ip.credits_used}"
            )

            if trial_ip.credits_used >= 3:
                print(
                    f"[MOBILE] guest trial_expired guest_id={guest_id} "
                    f"ip={client_ip} credits_used={trial_ip.credits_used}"
                )
                return Response({
                    "success": False,
                    "error": "trial_expired",
                    "message": "Trial expired. Please sign up for more credits."
                })

            # Generate openers from image
            reply, success = generate_mobile_openers_from_image(img_bytes, custom_instructions=custom_instructions)

            if success:
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
        logger.error(f"Generate openers from image error: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Generation failed", "message": str(e)})


@api_view(["POST"])
@permission_classes([AllowAny])
def recommended_openers(request):
    """Return recommended openers and count towards free use/subscription limits."""
    try:
        count_raw = request.data.get("count", 3)
        try:
            count = int(count_raw)
        except (TypeError, ValueError):
            count = 3

        openers = _select_recommended_openers(count)
        if not openers:
            return Response(
                {"success": False, "error": "no_openers", "message": "No openers available"},
                status=404,
            )

        if request.user.is_authenticated:
            chat_credit = ChatCredit.objects.get(user=request.user)
            return Response(
                {
                    "success": True,
                    "openers": [
                        {
                            "id": opener.id,
                            "message": opener.text,
                            "why_it_works": opener.why_it_works,
                            "image_url": opener.image.url if opener.image else None,
                        }
                        for opener in openers
                    ],
                    **_subscription_payload(chat_credit),
                }
            )

        # Guest path (no credit usage)
        return Response(
            {
                "success": True,
                "openers": [
                    {
                        "id": opener.id,
                        "message": opener.text,
                        "why_it_works": opener.why_it_works,
                        "image_url": opener.image.url if opener.image else None,
                    }
                    for opener in openers
                ],
            }
        )
    except ChatCredit.DoesNotExist:
        return Response(
            {"success": False, "error": "profile_required"},
            status=400,
        )
    except Exception as exc:
        logger.error("Recommended openers error: %s", exc, exc_info=True)
        return Response({"success": False, "error": "generation_failed"}, status=500)
