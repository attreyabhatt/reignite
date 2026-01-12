from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        request = context.get("request")
        if (
            getattr(request, "is_mobile_password_reset", False)
            and template_prefix.endswith("password_reset_key")
        ):
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
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        msg = self.render_mail(template_prefix, email, context)
        msg.from_email = from_email
        msg.send()
