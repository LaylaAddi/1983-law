# Generated migration for documents app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='title',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='documentsection',
            name='status',
            field=models.CharField(choices=[('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('needs_work', 'Needs Work'), ('completed', 'Completed'), ('not_applicable', 'Not Applicable')], default='not_started', max_length=20),
        ),
    ]
