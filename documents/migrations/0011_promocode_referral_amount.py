# Generated manually for custom referral amounts

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0010_promocode_name_alter_promocode_owner_payoutrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocode',
            name='referral_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('5.00'),
                help_text='Amount earned per referral (default $15.00)',
                max_digits=10,
            ),
        ),
    ]
