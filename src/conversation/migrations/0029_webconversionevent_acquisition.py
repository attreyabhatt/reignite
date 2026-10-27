from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conversation", "0028_chatcredit_mobile_full_access")]
    operations = [
        migrations.AddField(model_name="webconversionevent", name="landing_path", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="webconversionevent", name="acquisition_source", field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name="webconversionevent", name="acquisition_medium", field=models.CharField(blank=True, max_length=24)),
    ]
