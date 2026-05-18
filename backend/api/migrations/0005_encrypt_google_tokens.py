import api.fields
from django.db import migrations


def encrypt_existing_google_tokens(apps, schema_editor):
    from api.services.crypto import encrypt_text

    GoogleAccount = apps.get_model("api", "GoogleAccount")
    for account in GoogleAccount.objects.all().iterator():
        access_token = encrypt_text(account.access_token)
        refresh_token = encrypt_text(account.refresh_token)
        updates = {}
        if access_token != account.access_token:
            updates["access_token"] = access_token
        if refresh_token != account.refresh_token:
            updates["refresh_token"] = refresh_token
        if updates:
            GoogleAccount.objects.filter(pk=account.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_emailrecord_hidden_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="googleaccount",
            name="access_token",
            field=api.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name="googleaccount",
            name="refresh_token",
            field=api.fields.EncryptedTextField(blank=True),
        ),
        migrations.RunPython(encrypt_existing_google_tokens, migrations.RunPython.noop),
    ]
