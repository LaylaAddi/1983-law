# Generated migration for adding attorney fields to PlaintiffInfo

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_plaintiffinfo_name_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_name',
            field=models.CharField(blank=True, help_text='Full name of attorney', max_length=100),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_bar_number',
            field=models.CharField(blank=True, help_text='State bar number', max_length=50),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_firm_name',
            field=models.CharField(blank=True, help_text='Law firm name', max_length=200),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_street_address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_state',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_zip_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_fax',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='plaintiffinfo',
            name='attorney_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
