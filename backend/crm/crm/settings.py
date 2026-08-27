"""
Django settings for crm project.

Generated from the DemoCRM startproject template (Django 5.2).

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv
from celery.schedules import crontab


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / ".env", override=True)

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "CRM"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "12345"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = (
    os.getenv("ALLOWED_HOSTS").split(",") if os.getenv("ALLOWED_HOSTS") else []
)

# ======================================================
# CORS (React frontend dev server)
# ======================================================

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "audit_log",
    "Task",
    "FollowUp",
    "customer_management",
    "Notification",
    "CallForms",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "accounts.middleware.MustChangePasswordMiddleware",
]

ROOT_URLCONF = "crm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "crm.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

# settings.py

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ======================================================
# DRF-SCPECTACULAR (OpenAPI / Swagger)
# ======================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "DemoCRM API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {
            "name": "Accounts",
            "description": "Authentication, user profiles, roles, and permissions",
        },
        {"name": "Leads", "description": "Lead management and workflow operations"},
        {"name": "Customers", "description": "Customer management"},
        {"name": "Pipelines", "description": "Pipeline and pipeline stage management"},
        {
            "name": "Quotations",
            "description": "Quotation creation, workflow, approvals, and PDF generation",
        },
        {"name": "Tasks", "description": "Task management"},
        {
            "name": "Meetings",
            "description": "Meeting scheduling and participant management",
        },
        {"name": "Reminders", "description": "Reminder management"},
        {"name": "Follow Ups", "description": "Follow-up tracking and notes"},
        {"name": "Notifications", "description": "User notifications"},
        {"name": "Audit Logs", "description": "System audit logs"},
        {"name": "Lead Sources", "description": "Lead source management"},
        {"name": "Activities", "description": "Activity tracking"},
        {
            "name": "CallForms Templates",
            "description": "Dynamic call form templates, versions, and fields",
        },
        {
            "name": "CallForms Workflow",
            "description": "Call attempts, submissions, triggers, and timelines",
        },
        {
            "name": "CallForms Adhoc Proposals",
            "description": "Proposals for ad-hoc fields on call form templates",
        },
        {
            "name": "CallForms Indexed Values",
            "description": "Indexed submission values for fast lookup",
        },
    ],
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}

AUTH_USER_MODEL = "accounts.CustomUser"

# ======================================================
# CALL FORMS CONFIGURATION
# ======================================================

# Consecutive failed call attempts (NO_ANSWER / BUSY / CALLBACK) before the
# system starts suggesting "Mark Lead Lost" to agents. Suggestion only - a
# lost lead still requires an explicit reason via the existing workflow.
CALL_FORMS_MAX_FAILED_ATTEMPTS = int(os.getenv("CALL_FORMS_MAX_FAILED_ATTEMPTS", "5"))

# ======================================================
# EMAIL CONFIGURATION
# ======================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip("'\" ")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip("'\" ").lower() == "true"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip("'\" ")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").strip("'\" ")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER).strip("'\" ")

# ======================================================
# LOGGER
# ======================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "customer_management": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "Task": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "FollowUp": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "Notification": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
# ==============================================================================
# CELERY & REDIS SETTINGS
# ==============================================================================
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"


# CELERY BEAT PERIODIC SCHEDULES
CELERY_BEAT_SCHEDULE = {
    "send-task-due-reminders-daily": {
        "task": "Task.tasks.task_due_reminder_job",
        "schedule": crontab(hour=9, minute=0),
    },
    "process-meeting-reminders-every-minute": {
        "task": "Task.tasks.meeting_reminder_job",
        "schedule": crontab(minute="*"),
    },
}
