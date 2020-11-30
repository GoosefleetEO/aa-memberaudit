# Generated by Django 3.1.3 on 2020-11-29 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memberaudit", "0003_mail_entity"),
    ]

    operations = [
        migrations.RenameField(
            model_name="characterupdatestatus",
            old_name="error_message",
            new_name="last_error_message",
        ),
        migrations.AddField(
            model_name="characterupdatestatus",
            name="content_hash",
            field=models.CharField(default="", max_length=32),
        ),
        migrations.AlterField(
            model_name="characterupdatestatus",
            name="is_success",
            field=models.BooleanField(db_index=True, default=None, null=True),
        ),
    ]