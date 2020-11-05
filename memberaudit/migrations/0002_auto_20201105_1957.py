# Generated by Django 3.1.2 on 2020-11-05 19:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("eveuniverse", "0004_effect_longer_name"),
        ("memberaudit", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="doctrineship",
            name="ship_type",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="Ship type is used for visual presentation only. All skill requirements must be explicitly defined.",
                null=True,
                on_delete=django.db.models.deletion.SET_DEFAULT,
                to="eveuniverse.evetype",
            ),
        ),
    ]
