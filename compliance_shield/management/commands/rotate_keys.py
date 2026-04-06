"""
python manage.py rotate_keys --model myapp.UserProfile --field pan_number
                             --old-region IN --new-region IN

Re-encrypts a specific encrypted field across all records using the
current encryption key. Use after rotating ENCRYPTION_KEY_<REGION>.
"""

from django.core.management.base import BaseCommand, CommandError
from django.apps import apps


class Command(BaseCommand):
    help = 'Re-encrypts a sensitive field after key rotation.'

    def add_arguments(self, parser):
        parser.add_argument('--model',      required=True, help='app_label.ModelName e.g. accounts.UserProfile')
        parser.add_argument('--field',      required=True, help='Field name e.g. pan_number')
        parser.add_argument('--old-region', default=None,  help='Old region key (default: same as new)')
        parser.add_argument('--new-region', default='IN',  help='New region key')
        parser.add_argument('--dry-run',    action='store_true')

    def handle(self, *args, **options):
        model_path = options['model']
        field_name = options['field']
        old_region = options.get('old_region') or options['new_region']
        new_region = options['new_region']
        dry_run    = options['dry_run']

        try:
            app_label, model_name = model_path.split('.')
            model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise CommandError(f'Cannot find model {model_path}: {e}')

        storage_field = f'_{field_name}'
        index_field   = f'{field_name}_index'

        if not hasattr(model, storage_field):
            raise CommandError(
                f'{storage_field} not found on {model_path}. '
                f'Is {field_name} decorated with @sensitive_field?'
            )

        from compliance_shield.encryption import RegionalEncryption

        qs    = model.objects.exclude(**{f'{storage_field}__isnull': True})
        total = qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN — would rotate {total} records in {model_path}.{field_name}'
            ))
            return

        self.stdout.write(f'Rotating {total} records in {model_path}.{field_name}...')

        rotated = 0
        errors  = 0
        for obj in qs.iterator():
            try:
                encrypted = getattr(obj, storage_field)
                if not encrypted:
                    continue

                # Decrypt with old key
                plain = RegionalEncryption.decrypt(encrypted, old_region)
                if not plain:
                    continue

                # Invalidate cache so new key is loaded
                RegionalEncryption.invalidate_cache()

                # Re-encrypt with new key
                new_encrypted = RegionalEncryption.encrypt(plain, new_region)
                new_index     = RegionalEncryption.make_blind_index(plain, new_region)

                update_kwargs = {storage_field: new_encrypted}
                if hasattr(obj, index_field):
                    update_kwargs[index_field] = new_index

                model.objects.filter(pk=obj.pk).update(**update_kwargs)
                rotated += 1

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'  Error on pk={obj.pk}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nKey rotation complete.\n'
            f'  Rotated : {rotated}\n'
            f'  Errors  : {errors}\n'
        ))
