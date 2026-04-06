from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── SensitiveDataAccessLog ─────────────────────────────────────────
        migrations.CreateModel(
            name='SensitiveDataAccessLog',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('model_label', models.CharField(db_index=True, max_length=100)),
                ('object_id',   models.CharField(db_index=True, max_length=100)),
                ('field_name',  models.CharField(max_length=100)),
                ('field_type',  models.CharField(max_length=50)),
                ('action',      models.CharField(choices=[('READ','Field Read / Decrypted'),('WRITE','Field Written / Encrypted'),('SEARCH','Blind Index Search')], max_length=10)),
                ('accessed_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Sensitive Data Access Log', 'verbose_name_plural': 'Sensitive Data Access Logs', 'ordering': ['-accessed_at'], 'app_label': 'compliance_shield'},
        ),
        migrations.AddIndex(
            model_name='sensitivedataaccesslog',
            index=models.Index(fields=['model_label', 'object_id'], name='cs_audit_model_obj_idx'),
        ),
        migrations.AddIndex(
            model_name='sensitivedataaccesslog',
            index=models.Index(fields=['accessed_at'], name='cs_audit_accessed_idx'),
        ),

        # ── ConsentRecord ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='ConsentRecord',
            fields=[
                ('id',                 models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('consent_type',       models.CharField(max_length=50)),
                ('jurisdiction',       models.CharField(default='IN', max_length=10)),
                ('consent_text_shown', models.TextField()),
                ('consent_text_hash',  models.CharField(max_length=64)),
                ('consent_version',    models.CharField(default='v1.0.0', max_length=20)),
                ('granted',            models.BooleanField(default=False)),
                ('granted_at',         models.DateTimeField(blank=True, null=True)),
                ('withdrawn_at',       models.DateTimeField(blank=True, null=True)),
                ('ip_address',         models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent',         models.TextField(blank=True)),
                ('session_id',         models.CharField(blank=True, max_length=100)),
                ('created_at',         models.DateTimeField(auto_now_add=True)),
                ('user',               models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cs_consent_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Consent Record', 'verbose_name_plural': 'Consent Records', 'ordering': ['-created_at'], 'app_label': 'compliance_shield'},
        ),
        migrations.AddIndex(
            model_name='consentrecord',
            index=models.Index(fields=['user', 'consent_type', 'jurisdiction'], name='cs_consent_user_type_idx'),
        ),

        # ── DataDeletionRequest ────────────────────────────────────────────
        migrations.CreateModel(
            name='DataDeletionRequest',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('reason',       models.CharField(max_length=100)),
                ('consent_type', models.CharField(blank=True, max_length=50)),
                ('jurisdiction', models.CharField(default='IN', max_length=10)),
                ('status',       models.CharField(choices=[('pending','Pending'),('in_progress','In Progress'),('completed','Completed'),('rejected','Rejected')], default='pending', max_length=20)),
                ('ip_address',   models.GenericIPAddressField(blank=True, null=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('notes',        models.TextField(blank=True)),
                ('user',         models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cs_deletion_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Data Deletion Request', 'verbose_name_plural': 'Data Deletion Requests', 'ordering': ['-requested_at'], 'app_label': 'compliance_shield'},
        ),

        # ── DataSubjectRequest ─────────────────────────────────────────────
        migrations.CreateModel(
            name='DataSubjectRequest',
            fields=[
                ('id',                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('request_type',          models.CharField(max_length=50)),
                ('jurisdiction',          models.CharField(default='IN', max_length=10)),
                ('status',                models.CharField(default='received', max_length=20)),
                ('request_detail',        models.TextField()),
                ('supporting_document',   models.FileField(blank=True, null=True, upload_to='cs_dsr_documents/')),
                ('received_at',           models.DateTimeField(auto_now_add=True)),
                ('identity_verified_at',  models.DateTimeField(blank=True, null=True)),
                ('in_progress_at',        models.DateTimeField(blank=True, null=True)),
                ('completed_at',          models.DateTimeField(blank=True, null=True)),
                ('deadline_at',           models.DateTimeField(blank=True, null=True)),
                ('extended_deadline_at',  models.DateTimeField(blank=True, null=True)),
                ('deadline_days',         models.IntegerField(default=30)),
                ('response_detail',       models.TextField(blank=True)),
                ('rejection_reason',      models.TextField(blank=True)),
                ('disputed_information',  models.TextField(blank=True)),
                ('dispute_resolution',    models.TextField(blank=True)),
                ('ip_address',            models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent',            models.TextField(blank=True)),
                ('user',                  models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cs_dsr_requests', to=settings.AUTH_USER_MODEL)),
                ('handled_by',            models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cs_handled_dsr', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Data Subject Request', 'verbose_name_plural': 'Data Subject Requests', 'ordering': ['-received_at'], 'app_label': 'compliance_shield'},
        ),
        migrations.AddIndex(
            model_name='datasubjectrequest',
            index=models.Index(fields=['user', 'status'], name='cs_dsr_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='datasubjectrequest',
            index=models.Index(fields=['deadline_at'], name='cs_dsr_deadline_idx'),
        ),

        # ── DataRetentionPolicy ────────────────────────────────────────────
        migrations.CreateModel(
            name='DataRetentionPolicy',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('data_category',    models.CharField(max_length=50)),
                ('jurisdiction',     models.CharField(max_length=10)),
                ('retention_days',   models.IntegerField()),
                ('action_on_expiry', models.CharField(default='anonymise', max_length=20)),
                ('legal_basis',      models.TextField()),
                ('is_active',        models.BooleanField(default=True)),
                ('last_reviewed',    models.DateField(auto_now=True)),
                ('reviewed_by',      models.CharField(blank=True, max_length=100)),
                ('notes',            models.TextField(blank=True)),
            ],
            options={'verbose_name': 'Data Retention Policy', 'verbose_name_plural': 'Data Retention Policies', 'ordering': ['jurisdiction', 'data_category'], 'unique_together': {('data_category', 'jurisdiction')}, 'app_label': 'compliance_shield'},
        ),

        # ── DataRetentionLog ───────────────────────────────────────────────
        migrations.CreateModel(
            name='DataRetentionLog',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('data_category',    models.CharField(max_length=50)),
                ('jurisdiction',     models.CharField(max_length=10)),
                ('action_taken',     models.CharField(max_length=20)),
                ('records_affected', models.IntegerField(default=0)),
                ('run_at',           models.DateTimeField(auto_now_add=True)),
                ('run_by',           models.CharField(default='system', max_length=100)),
                ('detail',           models.TextField(blank=True)),
                ('errors',           models.TextField(blank=True)),
                ('policy',           models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='compliance_shield.dataretentionpolicy')),
            ],
            options={'verbose_name': 'Data Retention Log', 'verbose_name_plural': 'Data Retention Logs', 'ordering': ['-run_at'], 'app_label': 'compliance_shield'},
        ),

        # ── DataBreachRecord ───────────────────────────────────────────────
        migrations.CreateModel(
            name='DataBreachRecord',
            fields=[
                ('id',                       models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title',                    models.CharField(max_length=200)),
                ('breach_type',              models.CharField(max_length=30)),
                ('severity',                 models.CharField(max_length=10)),
                ('status',                   models.CharField(default='suspected', max_length=20)),
                ('discovered_at',            models.DateTimeField()),
                ('created_at',               models.DateTimeField(auto_now_add=True)),
                ('updated_at',               models.DateTimeField(auto_now=True)),
                ('affected_regions',         models.JSONField(default=list)),
                ('affected_data_categories', models.JSONField(default=list)),
                ('estimated_affected_users', models.IntegerField(blank=True, null=True)),
                ('confirmed_affected_users', models.IntegerField(blank=True, null=True)),
                ('nature_of_breach',         models.TextField()),
                ('likely_consequences',      models.TextField()),
                ('measures_taken',           models.TextField()),
                ('is_contained',             models.BooleanField(default=False)),
                ('contained_at',             models.DateTimeField(blank=True, null=True)),
                ('is_resolved',              models.BooleanField(default=False)),
                ('resolved_at',              models.DateTimeField(blank=True, null=True)),
                ('authority_notified_at',    models.JSONField(default=dict)),
                ('authority_reference',      models.JSONField(default=dict)),
                ('users_notified_at',        models.DateTimeField(blank=True, null=True)),
                ('users_notification_method',models.CharField(blank=True, max_length=100)),
                ('legal_hold',               models.BooleanField(default=False)),
                ('legal_hold_reason',        models.TextField(blank=True)),
                ('reported_by',              models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cs_reported_breaches', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Data Breach Record', 'verbose_name_plural': 'Data Breach Records', 'ordering': ['-discovered_at'], 'app_label': 'compliance_shield'},
        ),
        migrations.AddIndex(
            model_name='databreachrecord',
            index=models.Index(fields=['status'], name='cs_breach_status_idx'),
        ),
        migrations.AddIndex(
            model_name='databreachrecord',
            index=models.Index(fields=['severity'], name='cs_breach_severity_idx'),
        ),
    ]
