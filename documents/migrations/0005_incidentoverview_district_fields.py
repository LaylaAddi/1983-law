# Generated migration for adding federal district court fields to IncidentOverview

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_plaintiffinfo_attorney_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidentoverview',
            name='federal_district_court',
            field=models.CharField(blank=True, help_text='Federal district court for filing', max_length=255),
        ),
        migrations.AddField(
            model_name='incidentoverview',
            name='district_lookup_confidence',
            field=models.CharField(blank=True, choices=[('high', 'High Confidence'), ('medium', 'Medium Confidence'), ('low', 'Low Confidence')], max_length=20),
        ),
        migrations.AddField(
            model_name='incidentoverview',
            name='use_manual_court',
            field=models.BooleanField(default=False, help_text='Manually enter court instead of using lookup'),
        ),
    ]
