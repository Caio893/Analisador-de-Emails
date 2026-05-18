from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GoogleAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("access_token", models.TextField()),
                ("refresh_token", models.TextField(blank=True)),
                ("token_uri", models.URLField(default="https://oauth2.googleapis.com/token")),
                ("scopes", models.JSONField(blank=True, default=list)),
                ("token_expiry", models.DateTimeField(blank=True, null=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["email"],
            },
        ),
        migrations.CreateModel(
            name="EmailRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gmail_id", models.CharField(max_length=255)),
                ("thread_id", models.CharField(blank=True, max_length=255)),
                ("folder", models.CharField(choices=[("inbox", "Inbox"), ("spam", "Spam")], max_length=16)),
                ("from_name", models.CharField(blank=True, max_length=255)),
                ("from_email", models.EmailField(blank=True, max_length=254)),
                ("subject", models.CharField(blank=True, max_length=500)),
                ("snippet", models.TextField(blank=True)),
                ("body", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("unread", models.BooleanField(default=False)),
                ("raw_headers", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emails",
                        to="api.googleaccount",
                    ),
                ),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
        migrations.CreateModel(
            name="EmailAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "risk",
                    models.CharField(
                        choices=[
                            ("safe", "Safe"),
                            ("suspicious", "Suspicious"),
                            ("phishing", "Phishing"),
                        ],
                        max_length=16,
                    ),
                ),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("reason", models.TextField(blank=True)),
                ("signals", models.JSONField(blank=True, default=list)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("analyzed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "email",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis",
                        to="api.emailrecord",
                    ),
                ),
            ],
            options={
                "ordering": ["-analyzed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="emailrecord",
            index=models.Index(fields=["account", "folder", "-received_at"], name="api_emailre_account_c89922_idx"),
        ),
        migrations.AddIndex(
            model_name="emailrecord",
            index=models.Index(fields=["gmail_id"], name="api_emailre_gmail_i_d69ac0_idx"),
        ),
        migrations.AddConstraint(
            model_name="emailrecord",
            constraint=models.UniqueConstraint(
                fields=("account", "gmail_id"),
                name="unique_email_per_google_account",
            ),
        ),
        migrations.AddIndex(
            model_name="emailanalysis",
            index=models.Index(fields=["risk"], name="api_emailan_risk_66a708_idx"),
        ),
        migrations.AddIndex(
            model_name="emailanalysis",
            index=models.Index(fields=["-analyzed_at"], name="api_emailan_analyze_d14bc8_idx"),
        ),
    ]
