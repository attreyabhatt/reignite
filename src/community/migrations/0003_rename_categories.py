"""Rename community post categories and migrate existing data.

Old → New mapping:
  dating_advice → help_me_reply
  opening_line  → rate_my_profile
  success_story → wins
  app_feedback  → help_me_reply  (removed category, reassigned)
"""

from django.db import migrations, models


CATEGORY_MAP = {
    'dating_advice': 'help_me_reply',
    'opening_line': 'rate_my_profile',
    'success_story': 'wins',
    'app_feedback': 'help_me_reply',
}

REVERSE_MAP = {
    'help_me_reply': 'dating_advice',
    'rate_my_profile': 'opening_line',
    'wins': 'success_story',
}


def migrate_categories_forward(apps, schema_editor):
    CommunityPost = apps.get_model('community', 'CommunityPost')
    for old_val, new_val in CATEGORY_MAP.items():
        CommunityPost.objects.filter(category=old_val).update(category=new_val)


def migrate_categories_backward(apps, schema_editor):
    CommunityPost = apps.get_model('community', 'CommunityPost')
    for new_val, old_val in REVERSE_MAP.items():
        CommunityPost.objects.filter(category=new_val).update(category=old_val)


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0002_communitypost_is_anonymous_postpoll_contentreport_and_more'),
    ]

    operations = [
        # 1. Update the field choices (schema-only, no DB change for CharField)
        migrations.AlterField(
            model_name='communitypost',
            name='category',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('help_me_reply', 'Help Me Reply'),
                    ('rate_my_profile', 'Rate My Profile'),
                    ('wins', 'Wins'),
                ],
            ),
        ),
        # 2. Remap existing data
        migrations.RunPython(
            migrate_categories_forward,
            migrate_categories_backward,
        ),
    ]
