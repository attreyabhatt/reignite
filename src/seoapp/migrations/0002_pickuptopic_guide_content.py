from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("seoapp", "0001_initial")]
    operations = [migrations.AddField(
        model_name="pickuptopic", name="guide_content",
        field=models.JSONField(blank=True, default=dict),
    )]
