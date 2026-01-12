from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


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
