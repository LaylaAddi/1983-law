from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = 'api'

urlpatterns = [
    # JWT auth (for mobile app)
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Wizard endpoints
    path('wizard/<str:document_slug>/start/', views.wizard_start, name='wizard_start'),
    path('wizard/<str:session_slug>/status/', views.wizard_status, name='wizard_status'),
    path('wizard/<str:session_slug>/', views.wizard_get, name='wizard_get'),
    path('wizard/<str:session_slug>/step/<int:step_number>/', views.wizard_save_step, name='wizard_save_step'),
    path('wizard/<str:session_slug>/analyze/', views.wizard_analyze, name='wizard_analyze'),
    path('wizard/<str:session_slug>/analysis/', views.wizard_analysis_status, name='wizard_analysis_status'),
    path('wizard/<str:session_slug>/complete/', views.wizard_complete, name='wizard_complete'),
]
