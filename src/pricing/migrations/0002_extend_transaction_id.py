from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="creditpurchase",
            name="transaction_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
