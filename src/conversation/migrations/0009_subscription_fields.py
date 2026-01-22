from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversation', '0008_contactmessage_trialip_chatcredit_signup_bonus_given_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatcredit',
            name='is_subscribed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscriber_weekly_actions',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscriber_weekly_reset_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_auto_renewing',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_expiry',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_last_checked',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_platform',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_product_id',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscription_purchase_token',
            field=models.TextField(blank=True, null=True),
        ),
    ]
