"""
Django settings for Prime Reserve Bank Online Banking Web Application.
Educational Demonstration Project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env if present
env_path = BASE_DIR / '.env'
env_vars = {}
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                env_vars[key.strip()] = val.strip().strip('"').strip("'")

def get_env(key, default=None):
    return os.environ.get(key, env_vars.get(key, default))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env('SECRET_KEY', 'django-insecure-prime-reserve-bank-secret-key-2026-demo')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env('DEBUG', 'True').lower() in ('true', '1', 'yes')

hosts_raw = get_env('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver')
ALLOWED_HOSTS = [h.strip() for h in hosts_raw.split(',') if h.strip()]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Prime Reserve Bank Core Modules
    'accounts.apps.AccountsConfig',
    'banking.apps.BankingConfig',
    'transfers.apps.TransfersConfig',
    'beneficiaries.apps.BeneficiariesConfig',
    'transactions.apps.TransactionsConfig',
    'upi.apps.UpiConfig',
    'bills.apps.BillsConfig',
    'finance.apps.FinanceConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
                'accounts.context_processors.bank_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration
# Primary: MySQL (with PyMySQL)
# Fallback: SQLite (for easy local portable demonstration)
DB_ENGINE_TYPE = get_env('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE_TYPE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': get_env('DB_NAME', 'prime_reserve_bank_db'),
            'USER': get_env('DB_USER', 'root'),
            'PASSWORD': get_env('DB_PASSWORD', ''),
            'HOST': get_env('DB_HOST', '127.0.0.1'),
            'PORT': get_env('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Profile photos, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Banking Session Security
SESSION_COOKIE_AGE = 1800  # 30 minutes inactivity timeout
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Security Headers
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'

# Educational Demo Settings
BANK_NAME = 'PRIME RESERVE BANK'
BANK_TAGLINE = 'Banking Made Simple, Secure & Smarter.'
BANK_IFSC_PREFIX = 'PRMB'
IS_EDUCATIONAL_DEMO = True
DEMO_OTP_DISPLAY = get_env('DEMO_OTP_DISPLAY', 'True').lower() in ('true', '1', 'yes')

# Maximum file upload size (2MB)
MAX_UPLOAD_SIZE = 2 * 1024 * 1024

# Email Backend Configuration (SMTP / Console)
EMAIL_HOST_USER = get_env('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = get_env('EMAIL_HOST_PASSWORD', '').replace(' ', '').strip()
EMAIL_BACKEND = get_env(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend' if (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD) else 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = get_env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(get_env('EMAIL_PORT', '587'))
EMAIL_USE_TLS = get_env('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = get_env('DEFAULT_FROM_EMAIL', f"PRIME RESERVE BANK <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else 'PRIME RESERVE BANK <no-reply@primereservebank.demo>')
