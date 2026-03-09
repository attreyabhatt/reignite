from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from conversation.models import ChatCredit, WebAppConfig


class AccountAdapter(DefaultAccountAdapter):
    def send_password_reset_mail(self, user, email, context):
        request = context.get("request")
        if getattr(request, "is_mobile_password_reset", False):
            template_prefix = "account/email/mobile_password_reset_key"
            from_email = "FlirtFix <no-reply@tryagaintext.com>"
            subject = render_to_string(
                f"{template_prefix}_subject.txt", context
            ).strip()
            body = render_to_string(
                f"{template_prefix}_message.txt", context
            )
            EmailMessage(subject, body, from_email, [email]).send()
            return

        return super().send_password_reset_mail(user, email, context)

    def send_mail(self, template_prefix, email, context):
        msg = self.render_mail(template_prefix, email, context)
        msg.from_email = settings.DEFAULT_FROM_EMAIL
        msg.send()

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        if not commit:
            return user

        cfg = WebAppConfig.load()
        bonus_credits = cfg.signup_bonus_credits
        chat_credit, _ = ChatCredit.objects.get_or_create(
            user=user,
            defaults={
                "balance": bonus_credits,
                "signup_bonus_given": True,
                "total_earned": bonus_credits,
            },
        )

        update_fields = []
        if chat_credit.balance != bonus_credits:
            chat_credit.balance = bonus_credits
            update_fields.append("balance")
        if chat_credit.total_earned != bonus_credits:
            chat_credit.total_earned = bonus_credits
            update_fields.append("total_earned")
        if not chat_credit.signup_bonus_given:
            chat_credit.signup_bonus_given = True
            update_fields.append("signup_bonus_given")
        if update_fields:
            chat_credit.save(update_fields=update_fields)

        return user
