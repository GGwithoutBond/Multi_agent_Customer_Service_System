import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_debug_flag_parses_common_values():
    settings_true = Settings.model_validate({"SECRET_KEY": "secure-test-key-1234567890", "DEBUG": "ON"})
    assert settings_true.DEBUG is True

    settings_false = Settings.model_validate({"SECRET_KEY": "secure-test-key-1234567890", "DEBUG": "release"})
    assert settings_false.DEBUG is False


def test_secret_key_rejects_default_placeholder():
    with pytest.raises(ValidationError):
        Settings.model_validate({"SECRET_KEY": "your-secret-key-change-in-production", "DEBUG": False})


def test_secret_key_accepts_non_default_value():
    settings = Settings.model_validate({"SECRET_KEY": "unit-test-secret-key-123456", "DEBUG": False})
    assert settings.SECRET_KEY == "unit-test-secret-key-123456"
