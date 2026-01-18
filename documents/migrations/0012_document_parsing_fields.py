# Generated manually for background processing feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0011_promocode_referral_amount'),
        ('documents', '0012_alter_documentcaselaw_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='parsing_status',
            field=models.CharField(
                choices=[('idle', 'Idle'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')],
                default='idle',
                help_text='Current status of story parsing',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='parsing_result',
            field=models.JSONField(
                blank=True,
                help_text='Parsed sections from AI (stored for polling retrieval)',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='parsing_error',
            field=models.TextField(
                blank=True,
                help_text='Error message if parsing failed',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='parsing_started_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When parsing started (to detect stale jobs)',
                null=True,
            ),
        ),
    ]
