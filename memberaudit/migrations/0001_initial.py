# Generated by Django 2.2.10 on 2020-09-28 18:22

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('eveuniverse', '0002_load_eveunit'),
        ('authentication', '0017_remove_fleetup_permission'),
    ]

    operations = [
        migrations.CreateModel(
            name='Memberaudit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': (('basic_access', 'Can access this app'), ('unrestricted_access', 'Can view all characters and data')),
                'managed': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_sp', models.BigIntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('unallocated_sp', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('wallet_balance', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('last_sync', models.DateTimeField(blank=True, default=None, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('character_ownership', models.OneToOneField(help_text='character registered to member audit', on_delete=django.db.models.deletion.CASCADE, related_name='memberaudit_owner', to='authentication.CharacterOwnership')),
            ],
        ),
        migrations.CreateModel(
            name='Mail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mail_id', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('is_read', models.BooleanField(blank=True, default=None, null=True)),
                ('subject', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('body', models.TextField(blank=True, default=None, null=True)),
                ('timestamp', models.DateTimeField(blank=True, default=None, null=True)),
                ('character', models.ForeignKey(help_text='character this mail belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='mails', to='memberaudit.Character')),
                ('from_entity', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CharacterDetail',
            fields=[
                ('character', models.OneToOneField(help_text='character this details belongs to', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='details', serialize=False, to='memberaudit.Character')),
                ('birthday', models.DateTimeField()),
                ('description', models.TextField(blank=True, default='')),
                ('gender', models.CharField(choices=[('m', 'male'), ('f', 'female')], max_length=1)),
                ('security_status', models.FloatField(blank=True, default=None, null=True)),
                ('title', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='WalletJournalEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_id', models.BigIntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('amount', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('balance', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('context_id', models.BigIntegerField(blank=True, default=None, null=True)),
                ('context_id_type', models.CharField(choices=[('NON', 'undefined'), ('STA', 'station_id'), ('MTR', 'market_transaction_id'), ('CHR', 'character_id'), ('COR', 'corporation_id'), ('ALL', 'alliance_id'), ('EVE', 'eve_system'), ('INJ', 'industry_job_id'), ('CNT', 'contract_id'), ('PLN', 'planet_id'), ('SYS', 'system_id'), ('TYP', 'type_id ')], max_length=3)),
                ('date', models.DateTimeField()),
                ('description', models.TextField()),
                ('reason', models.TextField(blank=True, default='')),
                ('ref_type', models.CharField(max_length=32)),
                ('tax', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_journal', to='memberaudit.Character')),
                ('first_party', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='wallet_journal_entry_first_party_set', to='eveuniverse.EveEntity')),
                ('second_party', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='wallet_journal_entry_second_party_set', to='eveuniverse.EveEntity')),
                ('tax_receiver', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='wallet_journal_entry_tax_receiver_set', to='eveuniverse.EveEntity')),
            ],
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active_skill_level', models.PositiveIntegerField()),
                ('skillpoints_in_skill', models.BigIntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('trained_skill_level', models.PositiveIntegerField()),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='memberaudit.Character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveType')),
            ],
        ),
        migrations.CreateModel(
            name='MailRecipient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reciepents', to='memberaudit.Mail')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveEntity')),
            ],
        ),
        migrations.CreateModel(
            name='MailLabels',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label_id', models.PositiveIntegerField()),
                ('mail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='labels', to='memberaudit.Mail')),
            ],
        ),
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('list_id', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=254)),
                ('character', models.ForeignKey(help_text='character this mailling list belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='mailing_lists', to='memberaudit.Character')),
            ],
        ),
        migrations.AddField(
            model_name='mail',
            name='from_mailing_list',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='memberaudit.MailingList'),
        ),
        migrations.CreateModel(
            name='CorporationHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_id', models.PositiveIntegerField(db_index=True)),
                ('is_deleted', models.BooleanField(blank=True, db_index=True, default=None, null=True)),
                ('start_date', models.DateTimeField(db_index=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='corporation_history', to='memberaudit.Character')),
                ('corporation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveEntity')),
            ],
        ),
        migrations.AddConstraint(
            model_name='walletjournalentry',
            constraint=models.UniqueConstraint(fields=('character', 'entry_id'), name='functional_pk_walletjournalentry'),
        ),
        migrations.AddConstraint(
            model_name='skill',
            constraint=models.UniqueConstraint(fields=('character', 'eve_type'), name='functional_pk_skills'),
        ),
        migrations.AlterUniqueTogether(
            name='mailrecipient',
            unique_together={('mail', 'recipient')},
        ),
        migrations.AlterUniqueTogether(
            name='maillabels',
            unique_together={('mail', 'label_id')},
        ),
        migrations.AlterUniqueTogether(
            name='mailinglist',
            unique_together={('character', 'list_id')},
        ),
        migrations.AlterUniqueTogether(
            name='mail',
            unique_together={('character', 'mail_id')},
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='alliance',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='owner_alliances', to='eveuniverse.EveEntity'),
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='corporation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner_corporations', to='eveuniverse.EveEntity'),
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='eve_ancestry',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='eveuniverse.EveAncestry'),
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='eve_bloodline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveBloodline'),
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='faction',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='eveuniverse.EveFaction'),
        ),
        migrations.AddField(
            model_name='characterdetail',
            name='race',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.EveRace'),
        ),
    ]
