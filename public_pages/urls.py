from django.urls import path
from . import views

# Note: No app_name so 'home' URL name is globally accessible (used in base.html)

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('rights/', views.know_your_rights, name='know_your_rights'),
    path('rights/record-police/', views.right_to_record, name='right_to_record'),
    path('rights/section-1983/', views.section_1983, name='section_1983'),
    path('rights/violated/', views.rights_violated, name='rights_violated'),
    path('rights/first-amendment-auditors/', views.first_amendment_auditors, name='first_amendment_auditors'),
    path('rights/fourth-amendment/', views.fourth_amendment, name='fourth_amendment'),
    path('rights/fifth-amendment/', views.fifth_amendment, name='fifth_amendment'),
]
