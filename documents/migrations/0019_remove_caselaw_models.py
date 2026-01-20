# Migration to properly remove CaseLaw models that were created in 0007
# but later removed from models.py.
#
# This uses proper Django migration operations so Django's migration
# framework knows these models have been deleted and won't try to
# create new migrations to delete them.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0018_aiprompt'),
    ]

    operations = [
        # First remove the unique_together constraint from DocumentCaseLaw
        migrations.AlterUniqueTogether(
            name='documentcaselaw',
            unique_together=set(),
        ),
        # Then delete DocumentCaseLaw (has FK to CaseLaw, so delete first)
        migrations.DeleteModel(
            name='DocumentCaseLaw',
        ),
        # Finally delete CaseLaw
        migrations.DeleteModel(
            name='CaseLaw',
        ),
    ]
