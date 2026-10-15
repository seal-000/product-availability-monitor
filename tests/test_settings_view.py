import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from product_monitor import config
from product_monitor.ui.views import settings_view
from product_monitor.ui.views.settings_view import SettingsView


class FakeSettings:
    def __init__(self):
        self.values = {}

    def contains(self, key):
        return key in self.values

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.values[key] = value


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_settings_save_monitoring_and_notification_preferences(monkeypatch, qapp):
    settings = FakeSettings()
    monkeypatch.setattr(settings_view, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(settings_view.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)
    view = SettingsView()

    view._save_settings()

    assert settings.values["monitor/default_interval_seconds"] == 300
    assert not any(key.startswith("detector/") for key in settings.values)
    assert view.status.text() == "Settings saved."
    view.close()


def test_email_requires_complete_smtp_settings(monkeypatch, qapp):
    settings = FakeSettings()
    monkeypatch.setattr(settings_view, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(settings_view.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)
    view = SettingsView()
    view.email_enabled.setChecked(True)
    view.email_address.setText("recipient@example.com")

    view._save_settings()

    assert "Email not enabled: complete all SMTP fields." in view.status.text()
    assert settings.values["notifications/email_enabled"] is False
    view.close()


def test_unchecking_sms_is_saved_even_when_email_is_incomplete(monkeypatch, qapp):
    settings = FakeSettings()
    settings.values["notifications/sms_enabled"] = True
    monkeypatch.setattr(settings_view, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(settings_view.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)
    view = SettingsView()
    emitted = []
    view.settings_saved.connect(emitted.append)
    view.sms_enabled.setChecked(False)
    view.email_enabled.setChecked(True)

    view._save_settings()

    assert settings.values["notifications/sms_enabled"] is False
    assert emitted[0].sms_enabled is False
    view.close()


def test_email_addresses_with_surrounding_spaces_are_accepted(monkeypatch, qapp):
    settings = FakeSettings()
    monkeypatch.setattr(settings_view, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(settings_view.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(settings_view.keyring, "set_password", lambda *_args: None)
    view = SettingsView()
    view.email_enabled.setChecked(True)
    view.email_address.setText(" recipient@example.com ")
    view.smtp_host.setText("smtp.example.com")
    view.smtp_username.setText("user")
    view.smtp_password.setText("secret")
    view.email_sender.setText("sender@example.com ")

    view._save_settings()

    assert settings.values["notifications/email_enabled"] is True
    assert settings.values["notifications/email_address"] == "recipient@example.com"
    view.close()


def test_saving_email_settings_stores_smtp_password_in_keyring(monkeypatch, qapp):
    settings = FakeSettings()
    keyring_values = {}
    monkeypatch.setattr(settings_view, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    monkeypatch.setattr(settings_view.keyring, "get_password", lambda *_args: None)
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)

    def save_password(service, username, password):
        keyring_values[(service, username)] = password

    monkeypatch.setattr(settings_view.keyring, "set_password", save_password)
    view = SettingsView()
    view.email_enabled.setChecked(True)
    view.email_address.setText("recipient@example.com")
    view.smtp_host.setText("smtp.example.com")
    view.smtp_username.setText("smtp-user")
    view.smtp_password.setText("smtp-secret")
    view.email_sender.setText("sender@example.com")

    view._save_settings()

    assert settings.values["email/smtp_host"] == "smtp.example.com"
    assert settings.values["email/smtp_port"] == 587
    assert settings.values["email/username"] == "smtp-user"
    assert settings.values["email/sender_address"] == "sender@example.com"
    assert keyring_values[
        ("product-availability-monitor", "smtp-password")
    ] == "smtp-secret"
    assert view.status.text() == "Settings saved."
    view.close()
