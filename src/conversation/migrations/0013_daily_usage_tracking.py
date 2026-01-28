from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversation', '0012_seed_recommended_openers'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatcredit',
            name='subscriber_daily_openers',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscriber_daily_replies',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='chatcredit',
            name='subscriber_daily_reset_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
