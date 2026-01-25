import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.getenv('DEBUG', '0') == '1'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',      # Required for sitemap
    'django.contrib.sitemaps',   # XML sitemap for SEO
    # Third-party apps
    'ckeditor',
    # Local apps
    'accounts',
    'documents',
    'public_pages',
]

# Site ID for django.contrib.sites (required for sitemap)
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.app_branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL', '')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [
        'https://1983law.org',
        'https://www.1983law.org',
        'https://one983-law.onrender.com',
    ]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

# One-Time Document Purchases
DOCUMENT_PRICE_SINGLE = 49.00          # Single document
DOCUMENT_PRICE_3PACK = 99.00           # 3-pack ($33 each)
DOCUMENT_PRICE = DOCUMENT_PRICE_SINGLE  # Default/legacy compatibility

# Subscription Plans
SUBSCRIPTION_PRICE_MONTHLY = 29.00     # Per month
SUBSCRIPTION_PRICE_ANNUAL = 249.00     # Per year ($20.75/mo effective)

# Subscription AI Limits
SUBSCRIPTION_MONTHLY_AI_USES = 50      # AI uses per month for monthly subscribers
SUBSCRIPTION_ANNUAL_AI_USES = 999      # Effectively unlimited for annual

# Promo/Referral Discounts
PROMO_DISCOUNT_PERCENT = 20            # Discount for buyer using promo code

# Referral Payouts (first payment only for subscriptions)
REFERRAL_PAYOUT_SINGLE = 10.00         # Single doc referral
REFERRAL_PAYOUT_3PACK = 15.00          # 3-pack referral
REFERRAL_PAYOUT_MONTHLY = 10.00        # Monthly sub first payment referral
REFERRAL_PAYOUT_ANNUAL = 40.00         # Annual sub referral
REFERRAL_PAYOUT = REFERRAL_PAYOUT_SINGLE  # Default/legacy compatibility

# Free Tier Limits
FREE_AI_GENERATIONS = 3                # Per user across all documents
DRAFT_EXPIRY_HOURS = 48                # Hours before unpaid draft expires

# Paid Document Limits (one-time purchases)
PAID_AI_USES = 100                     # AI uses per paid document
PAID_EXPIRY_DAYS = 45                  # Days to complete paid document

# Stripe Configuration
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Price IDs (set in environment after creating in Stripe Dashboard)
STRIPE_PRICE_SINGLE = os.getenv('STRIPE_PRICE_SINGLE', '')
STRIPE_PRICE_3PACK = os.getenv('STRIPE_PRICE_3PACK', '')
STRIPE_PRICE_MONTHLY = os.getenv('STRIPE_PRICE_MONTHLY', '')
STRIPE_PRICE_ANNUAL = os.getenv('STRIPE_PRICE_ANNUAL', '')

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Authentication
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'public_pages:home'
LOGOUT_REDIRECT_URL = 'public_pages:home'

# Email Configuration
# For development: uses console backend (prints to terminal)
# For production: uses SMTP (Namecheap Private Email or similar)
if os.getenv('EMAIL_HOST'):
    # Production SMTP settings
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')  # e.g., mail.privateemail.com
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', '1') == '1'  # Use SSL for port 465
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '0') == '1'  # Use TLS for port 587
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # e.g., noreply@1983law.com
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
else:
    # Development: print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@1983law.com')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@1983law.com')

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# App Branding
APP_NAME = os.getenv('APP_NAME', '1983law.com')  # Used in footer and watermark
HEADER_APP_NAME = os.getenv('HEADER_APP_NAME', '1983 Law')  # Used in header/navbar

# CKEditor Configuration
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 400,
        'width': '100%',
        'removePlugins': 'elementspath',
        'resize_enabled': True,
    },
    'legal': {
        'toolbar': [
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source'],
            '/',
            ['Format', 'Styles'],
            ['Table', 'HorizontalRule'],
            ['Undo', 'Redo'],
        ],
        'height': 500,
        'width': '100%',
        'removePlugins': 'elementspath',
        'resize_enabled': True,
        'format_tags': 'p;h2;h3;h4;h5;h6',
        'stylesSet': [
            {'name': 'Alert Warning', 'element': 'div', 'attributes': {'class': 'alert alert-warning'}},
            {'name': 'Alert Info', 'element': 'div', 'attributes': {'class': 'alert alert-info'}},
            {'name': 'Alert Danger', 'element': 'div', 'attributes': {'class': 'alert alert-danger'}},
            {'name': 'Card', 'element': 'div', 'attributes': {'class': 'card mb-4'}},
        ],
    },
}
