# Generated by Django 4.0.5 on 2022-06-08 18:13

from django.db import migrations


def forwards(apps, schema_editor):
    Character = apps.get_model("memberaudit", "Character")
    for character in Character.objects.all():
        character.eve_character_id = character.character_ownership.character_id
        character.save()


class Migration(migrations.Migration):

    dependencies = [
        ("memberaudit", "0009_add_evecharacter_relation"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
