# Generated migration for adding is_test_user to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_test_user',
            field=models.BooleanField(default=False, help_text='Enable test features like auto-fill sample data'),
        ),
    ]
