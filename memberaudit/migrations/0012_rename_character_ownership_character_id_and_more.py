# Generated by Django 4.0.5 on 2022-06-08 19:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eveonline", "0016_character_names_are_not_unique"),
        ("memberaudit", "0011_alter_character_character_ownership"),
    ]

    operations = [
        migrations.RenameField(
            model_name="character",
            old_name="character_ownership",
            new_name="id",
        ),
        migrations.AlterField(
            model_name="character",
            name="eve_character",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberaudit_character",
                to="eveonline.evecharacter",
            ),
        ),
    ]
