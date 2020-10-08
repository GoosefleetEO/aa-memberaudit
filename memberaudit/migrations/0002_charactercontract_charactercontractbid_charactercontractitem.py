# Generated by Django 3.1.1 on 2020-10-07 23:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("eveuniverse", "0002_load_eveunit"),
        ("memberaudit", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CharacterContract",
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
                ("contract_id", models.IntegerField()),
                (
                    "availability",
                    models.CharField(
                        choices=[
                            ("AL", "alliance"),
                            ("CO", "corporation"),
                            ("PR", "personal"),
                            ("PU", "public"),
                        ],
                        help_text="To whom the contract is available",
                        max_length=2,
                    ),
                ),
                (
                    "buyout",
                    models.DecimalField(
                        decimal_places=2, default=None, max_digits=17, null=True
                    ),
                ),
                (
                    "collateral",
                    models.DecimalField(
                        decimal_places=2, default=None, max_digits=17, null=True
                    ),
                ),
                (
                    "contract_type",
                    models.CharField(
                        choices=[
                            ("AT", "auction"),
                            ("CR", "courier"),
                            ("IE", "item exchange"),
                            ("LN", "loan"),
                            ("UK", "unknown"),
                        ],
                        max_length=2,
                    ),
                ),
                ("date_accepted", models.DateTimeField(default=None, null=True)),
                ("date_completed", models.DateTimeField(default=None, null=True)),
                ("date_expired", models.DateTimeField()),
                ("date_issued", models.DateTimeField()),
                ("days_to_complete", models.IntegerField(default=None, null=True)),
                ("for_corporation", models.BooleanField()),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2, default=None, max_digits=17, null=True
                    ),
                ),
                (
                    "reward",
                    models.DecimalField(
                        decimal_places=2, default=None, max_digits=17, null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CA", "canceled"),
                            ("DL", "deleted"),
                            ("FL", "failed"),
                            ("FS", "finished"),
                            ("FC", "finished contractor"),
                            ("FI", "finished issuer"),
                            ("IP", "in progress"),
                            ("OS", "outstanding"),
                            ("RJ", "rejected"),
                            ("RV", "reversed"),
                        ],
                        max_length=2,
                    ),
                ),
                ("title", models.CharField(default="", max_length=100)),
                ("volume", models.FloatField(default=None, null=True)),
                (
                    "acceptor",
                    models.ForeignKey(
                        default=None,
                        help_text="Who will accept the contract if character",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acceptor_character_contracts",
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "acceptor_corporation",
                    models.ForeignKey(
                        default=None,
                        help_text="corporation of acceptor",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acceptor_corporation_contracts",
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "assignee",
                    models.ForeignKey(
                        default=None,
                        help_text="To whom the contract is assigned, can be a corporation or a character",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignee_character_contracts",
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contracts",
                        to="memberaudit.character",
                    ),
                ),
                (
                    "end_location",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contract_end_location",
                        to="memberaudit.location",
                    ),
                ),
                (
                    "issuer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issuer_character_contracts",
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "issuer_corporation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issuer_corporation_contracts",
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "start_location",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contract_start_location",
                        to="memberaudit.location",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterContractItem",
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
                ("record_id", models.PositiveIntegerField(db_index=True)),
                ("is_included", models.BooleanField()),
                ("is_singleton", models.BooleanField()),
                ("quantity", models.PositiveIntegerField()),
                ("raw_quantity", models.PositiveIntegerField(default=None, null=True)),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="memberaudit.charactercontract",
                    ),
                ),
                (
                    "eve_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="eveuniverse.evetype",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterContractBid",
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
                ("bid_id", models.PositiveIntegerField(db_index=True)),
                ("amount", models.FloatField()),
                ("date_bid", models.DateTimeField()),
                (
                    "bidder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="eveuniverse.eveentity",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bids",
                        to="memberaudit.charactercontract",
                    ),
                ),
            ],
        ),
    ]