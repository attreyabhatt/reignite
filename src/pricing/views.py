from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CreditPurchase
from conversation.models import ChatCredit
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.urls import reverse
from django.contrib.auth.models import User
from decouple import config

DODO_TEST_PRODUCT_IDS = {
    10: "pdt_QWDNC1hvRqnpHk4oxM9LK", 
    50: "pdt_9XcpTOPW3WWKdq0lwM9X3",
    200: "pdt_XT5MQEY7S7x1aBCbcdYeZ"
}

DODO_LIVE_PRODUCT_IDS = {
    10: "pdt_k5SWFFZjyJxIFfxmWM0zc",
    50: "pdt_rRouhnxqZCImG427QT7sC",
    200: "pdt_EGR8j3QjeTxjxvlsqRm6A",
}

def pricing(request):
    credit_packs = [
        {'amount': 10, 'price': 1.99},
        {'amount': 50, 'price': 6.99},
        {'amount': 200, 'price': 19.99},
    ]
    context = {'credit_packs': credit_packs}
    return render(request, 'pricing/pricing.html', context)

@login_required
def purchase_credits(request, amount):
    
    is_debug = config('DJANGO_DEBUG', default=False, cast=bool)
    
    if is_debug:
        product_id = DODO_TEST_PRODUCT_IDS.get(amount)
    else:
        product_id = DODO_LIVE_PRODUCT_IDS.get(amount)

    if not product_id:
        messages.error(request, "Invalid credit pack selected.")
        return redirect("pricing:pricing")

    # Optional: Add metadata to redirect URL (e.g., ?credits=50)
    redirect_url = request.build_absolute_uri(reverse("conversation_home"))
    
    # Choose test or live checkout base URL
    
    dodo_base_url = (
        "https://test.checkout.dodopayments.com/buy/"
        if is_debug else
        "https://checkout.dodopayments.com/buy/"
    )

    # Build full payment URL
    payment_url = (
        f"{dodo_base_url}{product_id}"
        f"?quantity=1&redirect_url={redirect_url}"
    )

    return redirect(payment_url)

@csrf_exempt
def dodo_webhook(request):
    is_debug = config('DJANGO_DEBUG', default=False, cast=bool)
    try:
        payload = json.loads(request.body)
        print(payload)
        # Dodo sends the payment object directly
        payment_id = payload['data']['payment_id']
        status = payload['data']['status']
        email = payload['data']['customer']['email']
        product_id = payload['data']['product_cart'][0]['product_id']
        amount_paid = payload['data']['settlement_amount'] / 100  # Paise → INR
        
        print(f"Payment ID: {payment_id}, Status: {status}, Email: {email}, Product ID: {product_id}, Amount Paid: {amount_paid}")

        if status != "succeeded":
            return JsonResponse({"status": "ignored", "reason": "Not a successful payment"}, status=200)

        if not email or not product_id:
            return JsonResponse({"status": "error", "message": "Missing email or product info"}, status=400)

        if is_debug:
            PRODUCT_TEST_CREDIT_MAPPING = {
                "pdt_QWDNC1hvRqnpHk4oxM9LK": 10,
                "pdt_9XcpTOPW3WWKdq0lwM9X3": 50,
                "pdt_XT5MQEY7S7x1aBCbcdYeZ": 200
            }
            credits = PRODUCT_TEST_CREDIT_MAPPING.get(product_id)
        else:
            PRODUCT_LIVE_CREDIT_MAPPING = {
                "pdt_k5SWFFZjyJxIFfxmWM0zc": 10,
                "pdt_rRouhnxqZCImG427QT7sC": 50,
                "pdt_EGR8j3QjeTxjxvlsqRm6A": 200
            }
            credits = PRODUCT_LIVE_CREDIT_MAPPING.get(product_id)

        if not credits:
            return JsonResponse({"status": "error", "message": "Unknown product ID"}, status=400)

        # Match user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"}, status=404)

        # Credit user account
        chat_credit, _ = ChatCredit.objects.get_or_create(user=user)
        chat_credit.balance += credits
        chat_credit.save()

        # Log the purchase
        CreditPurchase.objects.create(
            user=user,
            credits_purchased=credits,
            amount_paid=amount_paid,
            transaction_id=payment_id,
            payment_status="COMPLETED",
            payment_provider="dodo"
        )

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


