# Generated migration for adding story fields to Document

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_incidentoverview_district_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='story_text',
            field=models.TextField(blank=True, help_text='Raw story text from user (voice or typed)'),
        ),
        migrations.AddField(
            model_name='document',
            name='story_told_at',
            field=models.DateTimeField(blank=True, null=True, help_text='When the story was submitted'),
        ),
    ]
