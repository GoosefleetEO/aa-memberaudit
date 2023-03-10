# Generated by Django 4.0.8 on 2023-01-22 02:48

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('eveonline', '0017_alliance_and_corp_names_are_not_unique'),
        ('eveuniverse', '0007_evetype_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='General',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': (('basic_access', 'Can access this app, register, and view own characters'), ('share_characters', 'Can share his/her characters'), ('finder_access', 'Can access character finder feature'), ('reports_access', 'Can access reports feature'), ('characters_access', 'Can view characters owned by others'), ('exports_access', 'Can access data exports'), ('view_shared_characters', 'Can view shared characters'), ('view_same_corporation', 'Can view corporation characters'), ('view_same_alliance', 'Can view alliance characters'), ('view_everything', 'Can view all characters'), ('notified_on_character_removal', 'Notified when member drops character')),
                'managed': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('is_shared', models.BooleanField(default=False, help_text='Shared characters can be viewed by recruiters')),
                ('eve_character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='memberaudit_character', to='eveonline.evecharacter')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterContract',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_id', models.IntegerField()),
                ('availability', models.CharField(choices=[('AL', 'alliance'), ('CO', 'corporation'), ('PR', 'private'), ('PU', 'public')], help_text='To whom the contract is available', max_length=2)),
                ('buyout', models.DecimalField(decimal_places=2, default=None, max_digits=17, null=True)),
                ('collateral', models.DecimalField(decimal_places=2, default=None, max_digits=17, null=True)),
                ('contract_type', models.CharField(choices=[('AT', 'auction'), ('CR', 'courier'), ('IE', 'item exchange'), ('LN', 'loan'), ('UK', 'unknown')], max_length=2)),
                ('date_accepted', models.DateTimeField(default=None, null=True)),
                ('date_completed', models.DateTimeField(default=None, null=True)),
                ('date_expired', models.DateTimeField()),
                ('date_issued', models.DateTimeField()),
                ('days_to_complete', models.IntegerField(default=None, null=True)),
                ('for_corporation', models.BooleanField()),
                ('price', models.DecimalField(decimal_places=2, default=None, max_digits=17, null=True)),
                ('reward', models.DecimalField(decimal_places=2, default=None, max_digits=17, null=True)),
                ('status', models.CharField(choices=[('CA', 'canceled'), ('DL', 'deleted'), ('FL', 'failed'), ('FS', 'finished'), ('FC', 'finished contractor'), ('FI', 'finished issuer'), ('IP', 'in progress'), ('OS', 'outstanding'), ('RJ', 'rejected'), ('RV', 'reversed')], max_length=2)),
                ('title', models.CharField(default='', max_length=100)),
                ('volume', models.FloatField(default=None, null=True)),
                ('acceptor', models.ForeignKey(default=None, help_text='Who will accept the contract if character', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('acceptor_corporation', models.ForeignKey(default=None, help_text='corporation of acceptor', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('assignee', models.ForeignKey(default=None, help_text='To whom the contract is assigned, can be a corporation or a character', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='memberaudit.character')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterJumpClone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jump_clone_id', models.PositiveIntegerField(db_index=True)),
                ('name', models.CharField(default='', max_length=100)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jump_clones', to='memberaudit.character')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterWalletJournalEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_id', models.PositiveBigIntegerField(db_index=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('balance', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('context_id', models.PositiveBigIntegerField(default=None, null=True)),
                ('context_id_type', models.CharField(choices=[('NON', 'undefined'), ('STA', 'station ID'), ('MTR', 'market transaction ID'), ('CHR', 'character ID'), ('COR', 'corporation ID'), ('ALL', 'alliance ID'), ('EVE', 'eve system'), ('INJ', 'industry job ID'), ('CNT', 'contract ID'), ('PLN', 'planet ID'), ('SYS', 'system ID'), ('TYP', 'type ID')], max_length=3)),
                ('date', models.DateTimeField()),
                ('description', models.TextField()),
                ('reason', models.TextField()),
                ('ref_type', models.CharField(max_length=64)),
                ('tax', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=17, null=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_journal', to='memberaudit.character')),
                ('first_party', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveentity')),
                ('second_party', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveentity')),
                ('tax_receiver', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveentity')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='SkillSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_visible', models.BooleanField(db_index=True, default=True, help_text='Non visible skill sets are not shown to users on their character sheet and used for audit purposes only.')),
            ],
        ),
        migrations.CreateModel(
            name='EveShipType',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('eveuniverse.evetype',),
        ),
        migrations.CreateModel(
            name='EveSkillType',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('eveuniverse.evetype',),
        ),
        migrations.CreateModel(
            name='CharacterAttributes',
            fields=[
                ('character', models.OneToOneField(help_text='character these attributes belongs to', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='attributes', serialize=False, to='memberaudit.character')),
                ('accrued_remap_cooldown_date', models.DateTimeField(default=None, null=True)),
                ('last_remap_date', models.DateTimeField(default=None, null=True)),
                ('bonus_remaps', models.PositiveIntegerField()),
                ('charisma', models.PositiveIntegerField()),
                ('intelligence', models.PositiveIntegerField()),
                ('memory', models.PositiveIntegerField()),
                ('perception', models.PositiveIntegerField()),
                ('willpower', models.PositiveIntegerField()),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterDetails',
            fields=[
                ('character', models.OneToOneField(help_text='character this details belongs to', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='details', serialize=False, to='memberaudit.character')),
                ('birthday', models.DateTimeField()),
                ('description', models.TextField()),
                ('gender', models.CharField(choices=[('m', 'male'), ('f', 'female')], max_length=1)),
                ('name', models.CharField(max_length=100)),
                ('security_status', models.FloatField(default=None, null=True)),
                ('title', models.TextField()),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterLocation',
            fields=[
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='location', serialize=False, to='memberaudit.character')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterOnlineStatus',
            fields=[
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='online_status', serialize=False, to='memberaudit.character')),
                ('last_login', models.DateTimeField(default=None, null=True)),
                ('last_logout', models.DateTimeField(default=None, null=True)),
                ('logins', models.PositiveIntegerField(default=None, null=True)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterSkillpoints',
            fields=[
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='skillpoints', serialize=False, to='memberaudit.character')),
                ('total', models.PositiveBigIntegerField()),
                ('unallocated', models.PositiveIntegerField(default=None, null=True)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterWalletBalance',
            fields=[
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='wallet_balance', serialize=False, to='memberaudit.character')),
                ('total', models.DecimalField(decimal_places=2, max_digits=17)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='SkillSetSkill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('required_level', models.PositiveIntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('recommended_level', models.PositiveIntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='memberaudit.eveskilltype', verbose_name='skill')),
                ('skill_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='memberaudit.skillset')),
            ],
        ),
        migrations.CreateModel(
            name='SkillSetGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_doctrine', models.BooleanField(db_index=True, default=False, help_text='This enables a skill set group to show up correctly in doctrine reports')),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether this skill set group is in active use')),
                ('skill_sets', models.ManyToManyField(related_name='groups', to='memberaudit.skillset')),
            ],
        ),
        migrations.AddField(
            model_name='skillset',
            name='ship_type',
            field=models.ForeignKey(blank=True, default=None, help_text='Ship type is used for visual presentation only. All skill requirements must be explicitly defined.', null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='memberaudit.eveshiptype'),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.PositiveBigIntegerField(help_text='Eve Online location ID, either item ID for stations or structure ID for structures', primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='In-game name of this station or structure', max_length=100)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('eve_solar_system', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.evesolarsystem')),
                ('eve_type', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.evetype')),
                ('owner', models.ForeignKey(blank=True, default=None, help_text='corporation this station or structure belongs to', null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveentity')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='ComplianceGroupDesignation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
            ],
        ),
        migrations.CreateModel(
            name='CharacterWalletTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_id', models.PositiveBigIntegerField(db_index=True)),
                ('date', models.DateTimeField()),
                ('is_buy', models.BooleanField()),
                ('is_personal', models.BooleanField()),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=17)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_transactions', to='memberaudit.character')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveuniverse.evetype')),
                ('journal_ref', models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='wallet_transaction', to='memberaudit.characterwalletjournalentry')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memberaudit.location')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterUpdateStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(choices=[('assets', 'assets'), ('character_details', 'character details'), ('contacts', 'contacts'), ('contracts', 'contracts'), ('corporation_history', 'corporation history'), ('implants', 'implants'), ('jump_clones', 'jump clones'), ('location', 'location'), ('loyalty', 'loyalty'), ('mining_ledger', 'mining ledger'), ('online_status', 'online status'), ('ship', 'ship'), ('skills', 'skills'), ('skill_queue', 'skill queue'), ('skill_sets', 'skill sets'), ('wallet_balance', 'wallet balance'), ('wallet_journal', 'wallet journal'), ('wallet_transactions', 'wallet transactions'), ('attributes', 'attributes')], db_index=True, max_length=64)),
                ('is_success', models.BooleanField(db_index=True, default=None, null=True)),
                ('content_hash_1', models.CharField(default='', max_length=32)),
                ('content_hash_2', models.CharField(default='', max_length=32)),
                ('content_hash_3', models.CharField(default='', max_length=32)),
                ('last_error_message', models.TextField()),
                ('root_task_id', models.CharField(db_index=True, default='', help_text='ID of update_all_characters task that started this update', max_length=36)),
                ('parent_task_id', models.CharField(db_index=True, default='', help_text='ID of character_update task that started this update', max_length=36)),
                ('started_at', models.DateTimeField(db_index=True, default=None, null=True)),
                ('finished_at', models.DateTimeField(db_index=True, default=None, null=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='update_status_set', to='memberaudit.character')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterSkillSetCheck',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_set_checks', to='memberaudit.character')),
                ('failed_recommended_skills', models.ManyToManyField(related_name='failed_recommended_skill_set_checks', to='memberaudit.skillsetskill')),
                ('failed_required_skills', models.ManyToManyField(related_name='failed_required_skill_set_checks', to='memberaudit.skillsetskill')),
                ('skill_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memberaudit.skillset')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterSkillqueueEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('queue_position', models.PositiveIntegerField(db_index=True)),
                ('finish_date', models.DateTimeField(default=None, null=True)),
                ('finished_level', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('level_end_sp', models.PositiveIntegerField(default=None, null=True)),
                ('level_start_sp', models.PositiveIntegerField(default=None, null=True)),
                ('start_date', models.DateTimeField(default=None, null=True)),
                ('training_start_sp', models.PositiveIntegerField(default=None, null=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skillqueue', to='memberaudit.character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterSkill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active_skill_level', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('skillpoints_in_skill', models.PositiveBigIntegerField()),
                ('trained_skill_level', models.PositiveBigIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='memberaudit.character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterShip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('character', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ship', to='memberaudit.character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterMiningLedgerEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('quantity', models.PositiveIntegerField()),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mining_ledger', to='memberaudit.character')),
                ('eve_solar_system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evesolarsystem')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterLoyaltyEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loyalty_points', models.PositiveIntegerField()),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty_entries', to='memberaudit.character')),
                ('corporation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterJumpCloneImplant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
                ('jump_clone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='implants', to='memberaudit.characterjumpclone')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='characterjumpclone',
            name='location',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memberaudit.location'),
        ),
        migrations.CreateModel(
            name='CharacterImplant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='implants', to='memberaudit.character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterCorporationHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_id', models.PositiveIntegerField(db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=None, null=True)),
                ('start_date', models.DateTimeField(db_index=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='corporation_history', to='memberaudit.character')),
                ('corporation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterContractItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_id', models.PositiveIntegerField(db_index=True)),
                ('is_included', models.BooleanField(db_index=True)),
                ('is_singleton', models.BooleanField()),
                ('quantity', models.PositiveIntegerField()),
                ('raw_quantity', models.IntegerField(default=None, null=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='memberaudit.charactercontract')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterContractBid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bid_id', models.PositiveIntegerField(db_index=True)),
                ('amount', models.FloatField()),
                ('date_bid', models.DateTimeField()),
                ('bidder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bids', to='memberaudit.charactercontract')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='charactercontract',
            name='end_location',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contract_end_location', to='memberaudit.location'),
        ),
        migrations.AddField(
            model_name='charactercontract',
            name='issuer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity'),
        ),
        migrations.AddField(
            model_name='charactercontract',
            name='issuer_corporation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity'),
        ),
        migrations.AddField(
            model_name='charactercontract',
            name='start_location',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contract_start_location', to='memberaudit.location'),
        ),
        migrations.CreateModel(
            name='CharacterContactLabel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label_id', models.PositiveBigIntegerField()),
                ('name', models.CharField(max_length=100)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_labels', to='memberaudit.character')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterContact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_blocked', models.BooleanField(default=None, null=True)),
                ('is_watched', models.BooleanField(default=None, null=True)),
                ('standing', models.FloatField()),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='memberaudit.character')),
                ('eve_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity')),
                ('labels', models.ManyToManyField(related_name='contacts', to='memberaudit.charactercontactlabel')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='CharacterAsset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.PositiveBigIntegerField()),
                ('is_blueprint_copy', models.BooleanField(db_index=True, default=None, null=True)),
                ('is_singleton', models.BooleanField()),
                ('location_flag', models.CharField(max_length=100)),
                ('name', models.CharField(default='', max_length=100)),
                ('quantity', models.PositiveIntegerField()),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='memberaudit.character')),
                ('eve_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evetype')),
                ('location', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='memberaudit.location')),
                ('parent', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='memberaudit.characterasset')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.AddConstraint(
            model_name='skillsetskill',
            constraint=models.UniqueConstraint(fields=('skill_set', 'eve_type'), name='functional_pk_skillsetskill'),
        ),
        migrations.AddConstraint(
            model_name='characterwallettransaction',
            constraint=models.UniqueConstraint(fields=('character', 'transaction_id'), name='functional_pk_characterwallettransactions'),
        ),
        migrations.AddConstraint(
            model_name='characterwalletjournalentry',
            constraint=models.UniqueConstraint(fields=('character', 'entry_id'), name='functional_pk_characterwalletjournalentry'),
        ),
        migrations.AddConstraint(
            model_name='characterupdatestatus',
            constraint=models.UniqueConstraint(fields=('character', 'section'), name='functional_pk_charactersyncstatus'),
        ),
        migrations.AddConstraint(
            model_name='characterskillsetcheck',
            constraint=models.UniqueConstraint(fields=('character', 'skill_set'), name='functional_pk_characterskillsetcheck'),
        ),
        migrations.AddConstraint(
            model_name='characterskillqueueentry',
            constraint=models.UniqueConstraint(fields=('character', 'queue_position'), name='functional_pk_characterskillqueueentry'),
        ),
        migrations.AddConstraint(
            model_name='characterskill',
            constraint=models.UniqueConstraint(fields=('character', 'eve_type'), name='functional_pk_characterskill'),
        ),
        migrations.AddConstraint(
            model_name='characterminingledgerentry',
            constraint=models.UniqueConstraint(fields=('character', 'date', 'eve_solar_system', 'eve_type'), name='functional_pk_characterminingledgerentry'),
        ),
        migrations.AddConstraint(
            model_name='characterloyaltyentry',
            constraint=models.UniqueConstraint(fields=('character', 'corporation'), name='functional_pk_characterloyaltyentry'),
        ),
        migrations.AddField(
            model_name='characterlocation',
            name='eve_solar_system',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evesolarsystem'),
        ),
        migrations.AddField(
            model_name='characterlocation',
            name='location',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='memberaudit.location'),
        ),
        migrations.AddConstraint(
            model_name='characterjumpclone',
            constraint=models.UniqueConstraint(fields=('character', 'jump_clone_id'), name='functional_pk_characterjumpclone'),
        ),
        migrations.AddConstraint(
            model_name='characterimplant',
            constraint=models.UniqueConstraint(fields=('character', 'eve_type'), name='functional_pk_characterimplant'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='alliance',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveentity'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='corporation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.eveentity'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='eve_ancestry',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.eveancestry'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='eve_bloodline',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.evebloodline'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='eve_faction',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, related_name='+', to='eveuniverse.evefaction'),
        ),
        migrations.AddField(
            model_name='characterdetails',
            name='eve_race',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='eveuniverse.everace'),
        ),
        migrations.AddConstraint(
            model_name='charactercorporationhistory',
            constraint=models.UniqueConstraint(fields=('character', 'record_id'), name='functional_pk_charactercorporationhistory'),
        ),
        migrations.AddConstraint(
            model_name='charactercontract',
            constraint=models.UniqueConstraint(fields=('character', 'contract_id'), name='functional_pk_charactercontract'),
        ),
        migrations.AddConstraint(
            model_name='charactercontactlabel',
            constraint=models.UniqueConstraint(fields=('character', 'label_id'), name='functional_pk_characterlabel'),
        ),
        migrations.AddConstraint(
            model_name='charactercontact',
            constraint=models.UniqueConstraint(fields=('character', 'eve_entity'), name='functional_pk_charactercontact'),
        ),
        migrations.AddConstraint(
            model_name='characterasset',
            constraint=models.UniqueConstraint(fields=('character', 'item_id'), name='functional_pk_characterasset'),
        ),
    ]
