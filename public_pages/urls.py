from django.urls import path
from . import views

# Note: No app_name so 'home' URL name is globally accessible (used in base.html)

urlpatterns = [
    path('', views.landing_page, name='home'),
]
