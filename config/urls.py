import os
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from .sitemaps import sitemaps

# Admin URL path - can be rotated via environment variable for security
# Default is a random-looking path, NOT /admin/
ADMIN_URL = os.getenv('ADMIN_URL', 'manage-x7k9m2/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('api/v1/', include('documents.api.urls')),
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    path('legal/', include('accounts.legal_urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('public_pages.urls')),  # Public landing page
]
