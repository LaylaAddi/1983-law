from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/complete/', views.profile_complete, name='profile_complete'),

    # Password Reset (forgot password)
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Password Change (logged-in users)
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),

    # Subscriptions & Pricing
    path('pricing/', views.pricing, name='pricing'),
    path('subscribe/<str:plan>/', views.subscribe, name='subscribe'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/manage/', views.subscription_manage, name='subscription_manage'),
    path('subscription/webhook/', views.subscription_webhook, name='subscription_webhook'),
]
