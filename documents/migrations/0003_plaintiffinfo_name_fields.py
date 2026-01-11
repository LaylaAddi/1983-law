# Migration to convert full_name to first_name, middle_name, last_name

from django.db import migrations, models


def split_full_name(apps, schema_editor):
    """Split full_name into first_name, middle_name, last_name."""
    PlaintiffInfo = apps.get_model('documents', 'PlaintiffInfo')
    for plaintiff in PlaintiffInfo.objects.all():
        if plaintiff.full_name:
            parts = plaintiff.full_name.strip().split()
            if len(parts) >= 1:
                plaintiff.first_name = parts[0]
            if len(parts) >= 3:
                plaintiff.middle_name = parts[1]
                plaintiff.last_name = ' '.join(parts[2:])
            elif len(parts) == 2:
                plaintiff.last_name = parts[1]
            plaintiff.save()


def combine_names(apps, schema_editor):
    """Reverse: combine name fields back to full_name."""
    PlaintiffInfo = apps.get_model('documents', 'PlaintiffInfo')
    for plaintiff in PlaintiffInfo.objects.all():
        name_parts = [plaintiff.first_name, plaintiff.middle_name, plaintiff.last_name]
        plaintiff.full_name = ' '.join(part for part in name_parts if part)
        plaintiff.save()


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_alter_document_title_alter_documentsection_status'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='plaintiffinfo',
            name='first_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='middle_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='last_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        # Migrate data
        migrations.RunPython(split_full_name, combine_names),
        # Remove old field
        migrations.RemoveField(
            model_name='plaintiffinfo',
            name='full_name',
        ),
    ]
