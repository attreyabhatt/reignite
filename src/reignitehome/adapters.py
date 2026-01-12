from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        request = context.get("request")
        if (
            getattr(request, "is_mobile_password_reset", False)
            and template_prefix.endswith("password_reset_key")
        ):
            template_prefix = "account/email/mobile_password_reset_key"
            from_email = "FlirtFix <no-reply@tryagaintext.com>"
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        msg = self.render_mail(template_prefix, email, context)
        msg.from_email = from_email
        msg.send()
