from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conversation", "0027_webappconfig_models_and_thinking")]

    operations = [
        migrations.AddField(
            model_name="chatcredit",
            name="mobile_full_access",
            field=models.BooleanField(
                default=False,
                verbose_name="Complimentary mobile access",
                help_text="Grant all mobile subscription features without a purchase. Does not change web credits or billing.",
            ),
        ),
        migrations.AddField(
            model_name="chatcredit",
            name="mobile_access_expires_at",
            field=models.DateTimeField(
                blank=True, null=True,
                help_text="Optional expiry for complimentary mobile access. Leave blank for access until revoked.",
            ),
        ),
    ]
