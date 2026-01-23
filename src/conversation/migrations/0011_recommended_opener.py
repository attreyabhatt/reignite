from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversation", "0010_guesttrial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendedOpener",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("why_it_works", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="recommended_openers/")),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
