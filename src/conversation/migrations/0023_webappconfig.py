from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversation", "0022_mobileappconfig_community_default_sort"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebAppConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "primary_provider",
                    models.CharField(
                        choices=[("gemini", "Gemini"), ("gpt", "GPT")],
                        default="gemini",
                        help_text="Primary AI provider for webapp generation and OCR.",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Web App Config",
                "verbose_name_plural": "Web App Config",
            },
        ),
    ]

