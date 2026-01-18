# Migration to safely remove CaseLaw models that were created in 0007
# but later removed from models.py without a proper migration.
#
# This migration handles the case where the tables/constraints might
# not exist in all database states.

from django.db import migrations


def drop_caselaw_tables(apps, schema_editor):
    """
    Safely drop the CaseLaw tables if they exist.
    Uses raw SQL with CASCADE to handle constraints gracefully.
    """
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        # Drop tables with CASCADE - this handles all constraints automatically
        # IF EXISTS ensures it won't fail if tables don't exist
        cursor.execute('DROP TABLE IF EXISTS documents_documentcaselaw CASCADE')
        cursor.execute('DROP TABLE IF EXISTS documents_caselaw CASCADE')


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0018_aiprompt'),
    ]

    operations = [
        migrations.RunPython(
            drop_caselaw_tables,
            migrations.RunPython.noop,  # No reverse migration
        ),
    ]
