from __future__ import annotations

from dataclasses import replace

from app.config import SETTINGS


def test_settings_validate_development_noop():
    settings = replace(SETTINGS, app_env="development", database_url="", admin_api_key="", internal_api_key="", signing_key_pem="")
    settings.validate()


def test_settings_validate_production_requires_values():
    settings = replace(SETTINGS, app_env="production", database_url="", admin_api_key="", internal_api_key="", signing_key_pem="")
    try:
        settings.validate()
    except RuntimeError as exc:
        assert "DATABASE_URL" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
