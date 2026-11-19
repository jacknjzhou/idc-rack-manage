import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "drf_spectacular",
    "apps.rooms", "apps.racks", "apps.devices",
    "apps.placements", "apps.audit.apps.AuditConfig", "apps.accounts",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "APP_DIRS": True, "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB", "idc"),
    "USER": os.environ.get("POSTGRES_USER", "idc"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "idc"),
    "HOST": os.environ.get("POSTGRES_HOST", "db"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
}}
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
CORS_ALLOW_ALL_ORIGINS = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "IDC 机柜管理 API",
    "DESCRIPTION": "机房/机柜/设备/U位放置/容量校验/审计 REST API，Schema 驱动。",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
AUTH_USER_MODEL = "accounts.User"
