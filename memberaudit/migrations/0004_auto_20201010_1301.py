# Generated by Django 3.1.1 on 2020-10-10 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memberaudit", "0003_auto_20201008_1451"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="charactercontract",
            constraint=models.UniqueConstraint(
                fields=("character", "contract_id"),
                name="functional_pk_charactercontract",
            ),
        ),
    ]