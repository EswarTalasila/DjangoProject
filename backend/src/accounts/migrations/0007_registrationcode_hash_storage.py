from django.conf import settings
from django.db import migrations, models
from django.utils.crypto import salted_hmac


def _backfill_registration_code_hashes(apps, schema_editor):
    secret = getattr(settings, "SECRET_KEY", "")
    if not secret:
        raise RuntimeError(
            "SECRET_KEY must be configured before backfilling registration code hashes"
        )

    RegistrationCode = apps.get_model("accounts", "RegistrationCode")
    for record in RegistrationCode.objects.all().iterator():
        plaintext = str(record.code_hash or "").strip()
        if not plaintext:
            raise RuntimeError("RegistrationCode row has an empty code value during hash migration")
        normalized = plaintext.upper()
        record.code_prefix = normalized[:8]
        record.code_hash = salted_hmac(
            "registration-code",
            normalized,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()
        record.save(update_fields=["code_hash", "code_prefix"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_registrationcode_archived_at_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="registrationcode",
            old_name="code",
            new_name="code_hash",
        ),
        migrations.AddField(
            model_name="registrationcode",
            name="code_prefix",
            field=models.CharField(default="", max_length=8),
            preserve_default=False,
        ),
        migrations.RunPython(_backfill_registration_code_hashes, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="registrationcode",
            name="uq_registration_code",
        ),
        migrations.AddConstraint(
            model_name="registrationcode",
            constraint=models.UniqueConstraint(
                fields=("code_hash",),
                name="uq_registration_code_hash",
            ),
        ),
        migrations.RemoveIndex(
            model_name="registrationcode",
            name="idx_registration_code",
        ),
        migrations.AddIndex(
            model_name="registrationcode",
            index=models.Index(fields=["code_hash"], name="idx_registration_code_hash"),
        ),
        migrations.AddIndex(
            model_name="registrationcode",
            index=models.Index(fields=["code_prefix"], name="idx_registration_code_prefix"),
        ),
    ]
