from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import (
    EmailAuthenticationForm,
    UserRegistrationForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    CustomPasswordChangeForm,
    ProfileEditForm,
    ProfileCompleteForm,
)


class CustomLoginView(LoginView):
    """Login view with email authentication."""

    form_class = EmailAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('public_pages:home')

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().get_short_name()}!')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Logout view."""

    next_page = reverse_lazy('public_pages:home')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """User registration view."""

    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:profile_complete')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('public_pages:home')
        return super().dispatch(request, *args, **kwargs)

    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def form_valid(self, form):
        ip_address = self.get_client_ip()
        user = form.save(ip_address=ip_address)
        login(self.request, user)
        messages.success(self.request, 'Account created! Please complete your profile to continue.')
        return redirect(self.success_url)


class CustomPasswordResetView(PasswordResetView):
    """Password reset request view."""

    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Password reset email sent confirmation."""

    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Set new password after reset link clicked."""

    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Password reset complete confirmation."""

    template_name = 'accounts/password_reset_complete.html'


class CustomPasswordChangeView(PasswordChangeView):
    """Change password for logged-in users."""

    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully!')
        return super().form_valid(form)


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    """Password change complete confirmation."""

    template_name = 'accounts/password_change_done.html'


@login_required
def profile(request):
    """User profile view."""
    user = request.user

    # Get subscription info
    subscription = user.get_subscription()

    # Get document packs with remaining credits
    document_packs = user.document_packs.all().order_by('-created_at')

    # Get access summary
    access_summary = user.get_access_summary()

    # Get purchase history (document packs and subscription)
    from documents.models import Document
    paid_documents = Document.objects.filter(
        user=user,
        payment_status__in=['paid', 'finalized']
    ).order_by('-paid_at')[:10]

    context = {
        'subscription': subscription,
        'document_packs': document_packs,
        'access_summary': access_summary,
        'paid_documents': paid_documents,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile view."""
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'next_url': next_url,
    })


@login_required
def profile_complete(request):
    """Complete user profile - required before creating documents."""
    # If profile is already complete, redirect to home or next URL
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.user.has_complete_profile():
        messages.info(request, 'Your profile is already complete.')
        if next_url:
            return redirect(next_url)
        return redirect('public_pages:home')

    if request.method == 'POST':
        form = ProfileCompleteForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed! You can now create documents.')
            if next_url:
                return redirect(next_url)
            return redirect('public_pages:home')
    else:
        form = ProfileCompleteForm(instance=request.user)

    return render(request, 'accounts/profile_complete.html', {
        'form': form,
        'next_url': next_url,
    })


# Legal Pages
def _get_site_settings():
    """Helper to get site settings for legal pages."""
    from .models import SiteSettings
    return SiteSettings.get_settings()


def _get_legal_document(doc_type):
    """Helper to get legal document from database."""
    from .models import LegalDocument
    return LegalDocument.get_document(doc_type)


def _render_legal_page(request, doc_type, fallback_template):
    """
    Render a legal page.
    First checks for database content, falls back to template if not found.
    """
    settings = _get_site_settings()
    document = _get_legal_document(doc_type)

    if document:
        # Use database content
        return render(request, 'legal/document_base.html', {
            'settings': settings,
            'document': document,
        })
    else:
        # Fall back to hardcoded template
        return render(request, fallback_template, {
            'settings': settings,
        })


def terms_of_service(request):
    """Terms of Service page."""
    return _render_legal_page(request, 'terms', 'legal/terms.html')


def privacy_policy(request):
    """Privacy Policy page."""
    return _render_legal_page(request, 'privacy', 'legal/privacy.html')


def legal_disclaimer(request):
    """Legal Disclaimer page."""
    return _render_legal_page(request, 'disclaimer', 'legal/disclaimer.html')


def cookie_policy(request):
    """Cookie Policy page."""
    return _render_legal_page(request, 'cookies', 'legal/cookies.html')


# =============================================================================
# SUBSCRIPTION VIEWS
# =============================================================================

import stripe
from django.conf import settings as django_settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal

stripe.api_key = django_settings.STRIPE_SECRET_KEY


def pricing(request):
    """Display pricing page with all options."""
    from .models import Subscription

    # Capture document_id if user came from a specific document
    document_id = request.GET.get('document_id')

    context = {
        # One-time prices
        'price_single': django_settings.DOCUMENT_PRICE_SINGLE,

        # Subscription prices
        'price_monthly': django_settings.SUBSCRIPTION_PRICE_MONTHLY,
        'price_annual': django_settings.SUBSCRIPTION_PRICE_ANNUAL,
        'price_annual_per_month': round(django_settings.SUBSCRIPTION_PRICE_ANNUAL / 12, 2),

        # AI limits
        'monthly_ai_uses': django_settings.SUBSCRIPTION_MONTHLY_AI_USES,
        'annual_ai_uses': django_settings.SUBSCRIPTION_ANNUAL_AI_USES,
        'free_ai_uses': django_settings.FREE_AI_GENERATIONS,

        # Discount
        'promo_discount': django_settings.PROMO_DISCOUNT_PERCENT,

        # User subscription status
        'has_subscription': False,
        'subscription': None,

        # Document context for redirecting after purchase
        'document_id': document_id,
    }

    if request.user.is_authenticated:
        try:
            context['subscription'] = request.user.subscription
            context['has_subscription'] = request.user.subscription.is_active
        except Subscription.DoesNotExist:
            pass

    return render(request, 'accounts/pricing.html', context)


@login_required
def subscribe(request, plan):
    """Start subscription checkout process."""
    from .models import Subscription
    from documents.models import PromoCode

    if plan not in ['monthly', 'annual']:
        messages.error(request, 'Invalid subscription plan.')
        return redirect('accounts:pricing')

    # Check if user already has active subscription
    try:
        if request.user.subscription.is_active():
            messages.info(request, 'You already have an active subscription.')
            return redirect('accounts:subscription_manage')
    except Subscription.DoesNotExist:
        pass

    # Get price ID based on plan
    if plan == 'monthly':
        price_id = django_settings.STRIPE_PRICE_MONTHLY
        price_amount = django_settings.SUBSCRIPTION_PRICE_MONTHLY
    else:
        price_id = django_settings.STRIPE_PRICE_ANNUAL
        price_amount = django_settings.SUBSCRIPTION_PRICE_ANNUAL

    if not price_id:
        messages.error(request, 'Subscription not configured. Please contact support.')
        return redirect('accounts:pricing')

    # Handle promo code
    promo_code = None
    promo_code_str = request.GET.get('promo') or request.POST.get('promo_code', '').strip().upper()

    if promo_code_str:
        try:
            promo_code = PromoCode.objects.get(code=promo_code_str, is_active=True)
            if promo_code.owner == request.user:
                messages.error(request, 'You cannot use your own referral code.')
                promo_code = None
        except PromoCode.DoesNotExist:
            messages.error(request, 'Invalid promo code.')

    # Create or get Stripe customer
    try:
        # Check if user already has a Stripe customer ID
        existing_sub = Subscription.objects.filter(user=request.user).first()
        if existing_sub and existing_sub.stripe_customer_id:
            customer_id = existing_sub.stripe_customer_id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={'user_id': str(request.user.id)}
            )
            customer_id = customer.id

        # Build checkout session params
        checkout_params = {
            'customer': customer_id,
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': request.build_absolute_uri(
                reverse_lazy('accounts:subscription_success')
            ) + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': request.build_absolute_uri(
                reverse_lazy('accounts:pricing')
            ),
            'metadata': {
                'user_id': str(request.user.id),
                'plan': plan,
                'promo_code': promo_code.code if promo_code else '',
            },
        }

        # Apply promo discount if provided
        if promo_code:
            # Create a coupon for the discount
            checkout_params['discounts'] = [{
                'coupon': _get_or_create_promo_coupon(),
            }]
            request.session['subscription_promo_code'] = promo_code.code

        checkout_session = stripe.checkout.Session.create(**checkout_params)
        return redirect(checkout_session.url)

    except stripe.error.StripeError as e:
        messages.error(request, f'Payment error: {str(e)}')
        return redirect('accounts:pricing')


def _get_or_create_promo_coupon():
    """Get or create a Stripe coupon for promo discounts."""
    coupon_id = f"PROMO_{django_settings.PROMO_DISCOUNT_PERCENT}OFF"
    try:
        coupon = stripe.Coupon.retrieve(coupon_id)
    except stripe.error.InvalidRequestError:
        # Create the coupon
        coupon = stripe.Coupon.create(
            id=coupon_id,
            percent_off=django_settings.PROMO_DISCOUNT_PERCENT,
            duration='once',  # First payment only
            name=f'{django_settings.PROMO_DISCOUNT_PERCENT}% Off First Payment'
        )
    return coupon.id


@login_required
def subscription_success(request):
    """Handle successful subscription signup."""
    from .models import Subscription, SubscriptionReferral
    from documents.models import PromoCode
    import logging
    logger = logging.getLogger(__name__)

    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'Invalid checkout session.')
        return redirect('accounts:pricing')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = session.subscription

        if subscription_id:
            # Get subscription details from Stripe
            stripe_sub = stripe.Subscription.retrieve(subscription_id)

            # Log subscription data for debugging
            logger.info(f'Subscription retrieved: status={stripe_sub.status}, '
                       f'has_period_start={stripe_sub.get("current_period_start") is not None}, '
                       f'has_period_end={stripe_sub.get("current_period_end") is not None}')

            plan = session.metadata.get('plan', 'monthly')

            # Safely get period dates (may not be present for all subscription states)
            period_start = stripe_sub.get('current_period_start')
            period_end = stripe_sub.get('current_period_end')

            # Build defaults dict
            defaults = {
                'plan': plan,
                'status': stripe_sub.status,
                'stripe_subscription_id': subscription_id,
                'stripe_customer_id': stripe_sub.customer,
            }

            # Only set period dates if available
            if period_start:
                defaults['current_period_start'] = _timestamp_to_datetime(period_start)
            if period_end:
                defaults['current_period_end'] = _timestamp_to_datetime(period_end)

            # Create or update subscription record
            subscription, created = Subscription.objects.update_or_create(
                user=request.user,
                defaults=defaults
            )

            # Handle promo code referral
            promo_code_str = request.session.pop('subscription_promo_code', None) or session.metadata.get('promo_code')
            if promo_code_str and created:
                try:
                    promo_code = PromoCode.objects.get(code=promo_code_str, is_active=True)
                    referral_amount = (
                        django_settings.REFERRAL_PAYOUT_ANNUAL if plan == 'annual'
                        else django_settings.REFERRAL_PAYOUT_MONTHLY
                    )

                    # Create subscription referral
                    SubscriptionReferral.objects.create(
                        promo_code=promo_code,
                        subscription=subscription,
                        subscriber=request.user,
                        plan_type=plan,
                        first_payment_amount=Decimal(str(session.amount_total / 100)),
                        referral_amount=referral_amount,
                    )

                    # Update promo code stats
                    promo_code.record_usage(referral_amount)
                    subscription.promo_code_used = promo_code
                    subscription.save(update_fields=['promo_code_used'])

                except PromoCode.DoesNotExist:
                    pass

            messages.success(
                request,
                f'Welcome to Pro! Your {plan} subscription is now active.'
            )
            return redirect('accounts:subscription_manage')

    except stripe.error.StripeError as e:
        logger.error(f'Stripe error in subscription_success: {str(e)}')
        messages.error(request, f'Error confirming subscription: {str(e)}')
    except Exception as e:
        logger.error(f'Unexpected error in subscription_success: {str(e)}', exc_info=True)
        raise  # Re-raise to see full traceback in logs

    return redirect('accounts:pricing')


def _timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to datetime."""
    from django.utils import timezone
    from datetime import datetime
    return timezone.make_aware(datetime.fromtimestamp(timestamp))


@login_required
def subscription_manage(request):
    """Manage subscription - view status, cancel, etc."""
    from .models import Subscription

    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        messages.info(request, 'You do not have an active subscription.')
        return redirect('accounts:pricing')

    # Handle cancellation
    if request.method == 'POST' and request.POST.get('action') == 'cancel':
        try:
            # Cancel at period end (don't cancel immediately)
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
            subscription.save(update_fields=['cancel_at_period_end'])
            messages.success(
                request,
                'Your subscription will be canceled at the end of the current billing period.'
            )
        except stripe.error.StripeError as e:
            messages.error(request, f'Error canceling subscription: {str(e)}')

    # Handle reactivation
    if request.method == 'POST' and request.POST.get('action') == 'reactivate':
        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            subscription.cancel_at_period_end = False
            subscription.save(update_fields=['cancel_at_period_end'])
            messages.success(request, 'Your subscription has been reactivated.')
        except stripe.error.StripeError as e:
            messages.error(request, f'Error reactivating subscription: {str(e)}')

    context = {
        'subscription': subscription,
        'ai_remaining': subscription.get_ai_remaining(),
        'ai_limit': subscription.get_ai_limit(),
        'ai_used': subscription.ai_uses_this_period,
    }

    return render(request, 'accounts/subscription_manage.html', context)


@csrf_exempt
@require_POST
def subscription_webhook(request):
    """Handle Stripe webhook events for subscriptions."""
    from .models import Subscription

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, django_settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle subscription events
    if event['type'] == 'customer.subscription.updated':
        stripe_sub = event['data']['object']
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
            subscription.status = stripe_sub['status']

            # Safely get period dates (may not be present for all subscription states)
            period_start = stripe_sub.get('current_period_start')
            period_end = stripe_sub.get('current_period_end')

            if period_start:
                subscription.current_period_start = _timestamp_to_datetime(period_start)
            if period_end:
                subscription.current_period_end = _timestamp_to_datetime(period_end)

            subscription.cancel_at_period_end = stripe_sub.get('cancel_at_period_end', False)
            subscription.save()

            # Reset AI usage on new billing period
            if stripe_sub['status'] == 'active' and period_start:
                # Check if this is a new period
                old_period_end = subscription.current_period_end
                new_period_start = _timestamp_to_datetime(period_start)
                if old_period_end and new_period_start >= old_period_end:
                    subscription.reset_ai_usage()

        except Subscription.DoesNotExist:
            pass

    elif event['type'] == 'customer.subscription.deleted':
        stripe_sub = event['data']['object']
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
            subscription.status = 'canceled'
            from django.utils import timezone
            subscription.canceled_at = timezone.now()
            subscription.save()
        except Subscription.DoesNotExist:
            pass

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                subscription.status = 'past_due'
                subscription.save(update_fields=['status'])
            except Subscription.DoesNotExist:
                pass

    return HttpResponse(status=200)
