# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0019_remove_caselaw_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidentoverview',
            name='court_district_confirmed',
            field=models.BooleanField(default=False, help_text='User confirmed the court district is correct'),
        ),
    ]
