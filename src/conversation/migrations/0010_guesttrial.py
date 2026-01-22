from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversation', '0009_subscription_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='GuestTrial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('guest_id', models.CharField(max_length=64, unique=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True)),
                ('trial_used', models.BooleanField(default=False)),
                ('credits_used', models.IntegerField(default=0)),
            ],
        ),
    ]
