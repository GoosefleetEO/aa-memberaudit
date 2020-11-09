# Generated by Django 3.1.2 on 2020-11-08 15:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("memberaudit", "0002_auto_20201105_1957"),
    ]

    operations = [
        migrations.CreateModel(
            name="Settings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "compliant_user_group",
                    models.OneToOneField(
                        blank=True,
                        help_text="Group users that are compliant will be added to\n        automatically. The contents of this group should be considered\n        ephemeral, and users should not be manually added.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="auth.group",
                    ),
                ),
            ],
            options={
                "verbose_name": "settings",
                "verbose_name_plural": "settings",
            },
        ),
    ]