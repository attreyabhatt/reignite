from django.db import models

class TrialIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    trial_used = models.BooleanField(default=False)
