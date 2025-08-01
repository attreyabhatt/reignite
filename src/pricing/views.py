from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CreditPurchase
from conversation.models import ChatCredit

# 1. Pricing page
@login_required
def pricing(request):
    credit_packs = [
        {'amount': 10, 'price': 2.99},
        {'amount': 25, 'price': 5.99},
        {'amount': 50, 'price': 9.99},
    ]
    context = {'credit_packs': credit_packs}
    return render(request, 'pricing/pricing.html', context)

# 2. Mock purchase view (no payment gateway yet)
@login_required
def purchase_credits(request, amount):
        # amount = number of credits
        # Find price based on selected pack
        
        prices = {10: 2.99, 25: 5.99, 50: 9.99}
        price = prices.get(amount)
        
        if not price:
            messages.error(request, "Invalid credit pack.")
            return redirect('pricing:pricing')
        
        # In the real world: Redirect to payment gateway
        # For now, just add credits and mark as 'COMPLETED'
        chat_credit, created = ChatCredit.objects.get_or_create(user=request.user)
        chat_credit.balance += amount
        chat_credit.save()

        CreditPurchase.objects.create(
            user=request.user,
            credits_purchased=amount,
            amount_paid=price,
            payment_status='COMPLETED',
            payment_provider='manual'
        )
        messages.success(request, f"Successfully added {amount} credits to your account!")
        return redirect('conversation_home')

