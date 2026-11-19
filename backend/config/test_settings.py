from django.conf import settings

def test_core_apps_installed():
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS
    assert "apps.placements" in settings.INSTALLED_APPS

def test_db_is_postgresql():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

def test_schema_class_configured():
    assert settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"
