from django.urls import path
from . import views

app_name = 'legal'

urlpatterns = [
    path('terms/', views.terms_of_service, name='terms'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('disclaimer/', views.legal_disclaimer, name='disclaimer'),
    path('cookies/', views.cookie_policy, name='cookies'),
]
