from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def __init__(self, request=None):
        super().__init__(request)
        self._suppress_subject_prefix = False

    def get_email_subject_prefix(self):
        if self._suppress_subject_prefix:
            return ""
        return super().get_email_subject_prefix()

    def send_mail(self, template_prefix, email, context):
        request = getattr(self, "request", None) or context.get("request")
        if (
            getattr(request, "is_mobile_password_reset", False)
            and template_prefix.endswith("password_reset_key")
        ):
            template_prefix = "account/email/mobile_password_reset_key"
            from_email = "FlirtFix <no-reply@tryagaintext.com>"
            self._suppress_subject_prefix = True
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        msg = self.render_mail(template_prefix, email, context)
        msg.from_email = from_email
        msg.send()
