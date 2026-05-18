from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_trusted_sender_rule"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailrecord",
            name="hidden_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="emailrecord",
            index=models.Index(fields=["account", "hidden_at"], name="api_emailre_account_358774_idx"),
        ),
    ]
