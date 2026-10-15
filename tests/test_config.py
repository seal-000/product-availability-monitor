from product_monitor import config


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def contains(self, key):
        return key in self.values

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value


def patch_settings(monkeypatch, values=None):
    settings = FakeSettings(values)
    monkeypatch.setattr(config, "QSettings", lambda *_args: settings)
    return settings


def test_load_prefers_ui_values_and_keyring_token(monkeypatch):
    patch_settings(
        monkeypatch,
        {
            "notifications/sms_enabled": False,
            "notifications/email_enabled": True,
            "notifications/email_address": "saved@example.com",
            "twilio/account_sid": "saved-account",
        },
    )
    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "environment-account")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "environment-token")
    monkeypatch.setattr(
        config.keyring, "get_password", lambda *_args: "keyring-token"
    )

    app_config = config.AppConfig.load()

    assert app_config.sms_enabled is False
    assert app_config.email_enabled is True
    assert app_config.email_address == "saved@example.com"
    assert app_config.twilio.account_sid == "saved-account"
    assert app_config.twilio.auth_token == "keyring-token"


def test_loads_saved_smtp_settings_and_keyring_password(monkeypatch):
    patch_settings(
        monkeypatch,
        {
            "email/smtp_host": "smtp.example.com",
            "email/smtp_port": 465,
            "email/username": "smtp-user",
            "email/sender_address": "sender@example.com",
        },
    )
    monkeypatch.setattr(
        config.keyring,
        "get_password",
        lambda _service, username: {
            config.KEYRING_TOKEN_USERNAME: None,
            config.KEYRING_SMTP_PASSWORD_USERNAME: "smtp-secret",
        }[username],
    )

    app_config = config.AppConfig.load()

    assert app_config.email.smtp_host == "smtp.example.com"
    assert app_config.email.smtp_port == 465
    assert app_config.email.username == "smtp-user"
    assert app_config.email.password == "smtp-secret"
    assert app_config.email.sender_address == "sender@example.com"


def test_load_uses_environment_values_when_ui_values_are_missing(monkeypatch):
    patch_settings(monkeypatch)
    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "environment-account")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "environment-token")
    monkeypatch.setenv("TWILIO_FROM_PHONE_NUMBER", "+15550000001")
    monkeypatch.setenv("TWILIO_TO_PHONE_NUMBER", "+15550000002")
    monkeypatch.setenv("DEFAULT_INTERVAL_SECONDS", "45")
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)

    app_config = config.AppConfig.load()

    assert app_config.sms_enabled is True
    assert app_config.default_interval_seconds == 45
    assert app_config.twilio.is_configured is True
    assert app_config.has_configured_notification is True


def test_load_uses_default_interval_when_environment_value_is_invalid(monkeypatch):
    patch_settings(monkeypatch)
    monkeypatch.setenv("DEFAULT_INTERVAL_SECONDS", "not-a-number")
    monkeypatch.setattr(config.keyring, "get_password", lambda *_args: None)

    app_config = config.AppConfig.load()

    assert app_config.default_interval_seconds == 300


def test_notification_readiness_respects_enabled_channels():
    twilio = config.TwilioConfig(
        account_sid="account",
        auth_token="token",
        from_phone_number="+15550000001",
        to_phone_number="+15550000002",
    )

    sms_config = config.AppConfig(twilio=twilio, sms_enabled=True)
    email_config = config.AppConfig(
        twilio=config.TwilioConfig(),
        email_enabled=True,
        email_address="user@example.com",
    )
    configured_email_config = config.AppConfig(
        twilio=config.TwilioConfig(),
        email_enabled=True,
        email_address="user@example.com",
        email=config.EmailConfig(
            smtp_host="smtp.example.com",
            username="user@example.com",
            password="secret",
            sender_address="sender@example.com",
        ),
    )
    disabled_config = config.AppConfig(twilio=twilio)

    assert sms_config.has_configured_notification is True
    assert email_config.has_configured_notification is False
    assert configured_email_config.has_configured_notification is True
    assert disabled_config.has_configured_notification is False
