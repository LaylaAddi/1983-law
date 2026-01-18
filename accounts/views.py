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
        return reverse_lazy('home')

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().get_short_name()}!')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Logout view."""

    next_page = reverse_lazy('home')

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
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
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
    return render(request, 'accounts/profile.html')


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
        return redirect('home')

    if request.method == 'POST':
        form = ProfileCompleteForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed! You can now create documents.')
            if next_url:
                return redirect(next_url)
            return redirect('home')
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


def terms_of_service(request):
    """Terms of Service page."""
    return render(request, 'legal/terms.html', {
        'settings': _get_site_settings(),
    })


def privacy_policy(request):
    """Privacy Policy page."""
    return render(request, 'legal/privacy.html', {
        'settings': _get_site_settings(),
    })


def legal_disclaimer(request):
    """Legal Disclaimer page."""
    return render(request, 'legal/disclaimer.html', {
        'settings': _get_site_settings(),
    })


def cookie_policy(request):
    """Cookie Policy page."""
    return render(request, 'legal/cookies.html', {
        'settings': _get_site_settings(),
    })
