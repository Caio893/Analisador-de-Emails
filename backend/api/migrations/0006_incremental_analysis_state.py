from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_encrypt_google_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="googleaccount",
            name="gmail_history_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="googleaccount",
            name="gmail_watch_expiration",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emailrecord",
            name="content_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="emailrecord",
            name="gmail_history_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="emailanalysis",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="emailanalysis",
            name="content_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="emailanalysis",
            name="last_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="emailanalysis",
            name="prompt_version",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="emailanalysis",
            name="status",
            field=models.CharField(
                choices=[
                    ("local", "Local heuristic"),
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="completed",
                max_length=16,
            ),
        ),
    ]
