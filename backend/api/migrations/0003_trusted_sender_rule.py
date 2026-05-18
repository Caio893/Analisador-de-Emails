from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_email_metadata_and_classification"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrustedSenderRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rule_type", models.CharField(choices=[("email", "Email"), ("domain", "Domain")], max_length=16)),
                ("value", models.CharField(max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trusted_sender_rules",
                        to="api.googleaccount",
                    ),
                ),
            ],
            options={
                "ordering": ["rule_type", "value"],
            },
        ),
        migrations.AddConstraint(
            model_name="trustedsenderrule",
            constraint=models.UniqueConstraint(
                fields=("account", "rule_type", "value"),
                name="unique_trusted_sender_rule_per_account",
            ),
        ),
        migrations.AddIndex(
            model_name="trustedsenderrule",
            index=models.Index(
                fields=["account", "rule_type", "value", "enabled"],
                name="api_trusted_account_bba5f7_idx",
            ),
        ),
    ]
