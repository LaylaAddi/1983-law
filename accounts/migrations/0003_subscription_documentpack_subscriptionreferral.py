# Generated migration for subscription system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_footer_contact_info'),
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan', models.CharField(choices=[('monthly', 'Monthly ($29/mo)'), ('annual', 'Annual ($249/yr)')], max_length=20)),
                ('status', models.CharField(choices=[('active', 'Active'), ('past_due', 'Past Due'), ('canceled', 'Canceled'), ('unpaid', 'Unpaid'), ('trialing', 'Trialing'), ('incomplete', 'Incomplete'), ('incomplete_expired', 'Incomplete Expired')], default='incomplete', max_length=20)),
                ('stripe_subscription_id', models.CharField(help_text='Stripe Subscription ID (sub_xxx)', max_length=255, unique=True)),
                ('stripe_customer_id', models.CharField(help_text='Stripe Customer ID (cus_xxx)', max_length=255)),
                ('current_period_start', models.DateTimeField(blank=True, null=True)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('cancel_at_period_end', models.BooleanField(default=False, help_text='If true, subscription will cancel at period end')),
                ('ai_uses_this_period', models.IntegerField(default=0)),
                ('ai_period_reset_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('canceled_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
                ('promo_code_used', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscriptions', to='documents.promocode')),
            ],
            options={
                'verbose_name': 'Subscription',
                'verbose_name_plural': 'Subscriptions',
            },
        ),
        migrations.CreateModel(
            name='DocumentPack',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pack_type', models.CharField(choices=[('single', 'Single Document'), ('3pack', '3-Document Pack')], max_length=20)),
                ('documents_included', models.IntegerField(help_text='Number of documents included')),
                ('documents_used', models.IntegerField(default=0, help_text='Number of documents used')),
                ('stripe_payment_id', models.CharField(help_text='Stripe Payment Intent ID', max_length=255)),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_packs', to=settings.AUTH_USER_MODEL)),
                ('promo_code_used', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_packs', to='documents.promocode')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SubscriptionReferral',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_type', models.CharField(max_length=20)),
                ('first_payment_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('referral_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payout_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid')], default='pending', max_length=20)),
                ('payout_reference', models.CharField(blank=True, max_length=255)),
                ('payout_date', models.DateTimeField(blank=True, null=True)),
                ('payout_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('promo_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_referrals', to='documents.promocode')),
                ('subscriber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_referrals_received', to=settings.AUTH_USER_MODEL)),
                ('subscription', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='referral', to='accounts.subscription')),
            ],
            options={
                'verbose_name': 'Subscription Referral',
                'verbose_name_plural': 'Subscription Referrals',
                'ordering': ['-created_at'],
            },
        ),
    ]
