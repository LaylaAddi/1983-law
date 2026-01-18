# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_witness_enhanced_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='generated_complaint',
            field=models.TextField(blank=True, help_text='Cached AI-generated legal complaint document'),
        ),
        migrations.AddField(
            model_name='document',
            name='generated_at',
            field=models.DateTimeField(blank=True, null=True, help_text='When the complaint was last generated'),
        ),
    ]
