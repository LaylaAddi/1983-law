# Generated manually for witness enhancement feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_defendant_agency_inferred'),
        ('documents', '0014_merge_20260117_1635'),
    ]

    operations = [
        migrations.AddField(
            model_name='witness',
            name='has_evidence',
            field=models.BooleanField(
                default=False,
                help_text='Did this witness capture video/photo evidence?',
            ),
        ),
        migrations.AddField(
            model_name='witness',
            name='evidence_description',
            field=models.TextField(
                blank=True,
                help_text='Describe what they recorded (video, photos, audio)',
            ),
        ),
        migrations.AddField(
            model_name='witness',
            name='prior_interactions',
            field=models.TextField(
                blank=True,
                help_text='Any prior interactions this witness had with the defendant(s)',
            ),
        ),
        migrations.AddField(
            model_name='witness',
            name='additional_notes',
            field=models.TextField(
                blank=True,
                help_text='Any other relevant information about this witness',
            ),
        ),
    ]
