# Generated by Django 3.1.1 on 2020-10-17 18:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("memberaudit", "0012_doctrines_addon"),
    ]

    operations = [
        migrations.RenameField(
            model_name="charactercontact",
            old_name="contact",
            new_name="eve_entity",
        ),
    ]
