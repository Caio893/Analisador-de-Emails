from django.db import migrations, models


def migrate_risk_labels(apps, _schema_editor):
    EmailAnalysis = apps.get_model("api", "EmailAnalysis")
    EmailAnalysis.objects.filter(risk="safe").update(risk="trusted")
    EmailAnalysis.objects.filter(risk="phishing").update(risk="dangerous")


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailrecord",
            name="attachment_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="emailrecord",
            name="has_attachments",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="emailrecord",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(migrate_risk_labels, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="emailanalysis",
            name="risk",
            field=models.CharField(
                choices=[
                    ("trusted", "Trusted"),
                    ("slightly_trusted", "Slightly trusted"),
                    ("suspicious", "Suspicious"),
                    ("dangerous", "Dangerous"),
                ],
                max_length=16,
            ),
        ),
    ]
