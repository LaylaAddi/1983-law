# Generated manually for PDF background generation feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0015_document_complaint_cache'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='pdf_status',
            field=models.CharField(
                choices=[('idle', 'Idle'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')],
                default='idle',
                help_text='Current status of PDF generation',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='pdf_progress_stage',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Current stage of PDF generation for progress display',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='pdf_error',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Error message if PDF generation failed',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='pdf_started_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When PDF generation started (to detect stale jobs)',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='pdf_file_path',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Path to generated PDF file',
                max_length=500,
            ),
        ),
    ]
