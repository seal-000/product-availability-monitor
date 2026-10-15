
"""Load notification and monitor settings from the UI store and environment."""

from dataclasses import dataclass, field
import os

import keyring
from dotenv import load_dotenv
from PyQt6.QtCore import QSettings

load_dotenv()

SETTINGS_ORGANIZATION = "Product Monitor"
SETTINGS_APPLICATION = "Product Availability Monitor"
KEYRING_SERVICE = "product-availability-monitor"
KEYRING_TOKEN_USERNAME = "twilio-auth-token"
KEYRING_SMTP_PASSWORD_USERNAME = "smtp-password"


def _setting_or_environment(settings: QSettings, setting_key: str, env_key: str) -> str:
    """Prefer a non-empty value saved by the UI, then use the environment."""
    saved_value = settings.value(setting_key, "", type=str).strip()
    return saved_value or os.getenv(env_key, "").strip()


def _boolean_setting(settings: QSettings, setting_key: str, env_key: str, default: bool) -> bool:
    if settings.contains(setting_key):
        return settings.value(setting_key, default, type=bool)

    value = os.getenv(env_key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _integer_setting(settings: QSettings, setting_key: str, env_key: str, default: int) -> int:
    value = settings.value(setting_key, None)
    if value is None:
        value = os.getenv(env_key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class TwilioConfig:
    account_sid: str = ""
    auth_token: str = ""
    from_phone_number: str = ""
    to_phone_number: str = ""
    message_body: str = ""

    @property
    def is_configured(self) -> bool:
        return all((
            self.account_sid,
            self.auth_token,
            self.from_phone_number,
            self.to_phone_number,
        ))


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender_address: str = ""

    @property
    def is_configured(self) -> bool:
        return all((
            self.smtp_host,
            self.smtp_port,
            self.username,
            self.password,
            self.sender_address,
        ))


@dataclass
class AppConfig:
    twilio: TwilioConfig
    sms_enabled: bool = False
    email_enabled: bool = False
    email_address: str = ""
    email: EmailConfig = field(default_factory=EmailConfig)
    desktop_notifications_enabled: bool = False
    default_interval_seconds: int = 300

    @property
    def has_configured_notification(self) -> bool:
        return (
            (self.sms_enabled and self.twilio.is_configured)
            or (
                self.email_enabled
                and bool(self.email_address)
                and self.email.is_configured
            )
        )

    @classmethod
    def load(cls) -> "AppConfig":
        """Load UI settings first, with environment variables as defaults."""
        settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)

        try:
            auth_token = keyring.get_password(
                KEYRING_SERVICE, KEYRING_TOKEN_USERNAME
            ) or ""
        except keyring.errors.KeyringError:
            auth_token = ""
        auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "").strip()

        try:
            smtp_password = keyring.get_password(
                KEYRING_SERVICE, KEYRING_SMTP_PASSWORD_USERNAME
            ) or ""
        except keyring.errors.KeyringError:
            smtp_password = ""
        smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "").strip()

        twilio = TwilioConfig(
            account_sid=_setting_or_environment(
                settings, "twilio/account_sid", "TWILIO_ACCOUNT_SID"
            ),
            auth_token=auth_token,
            from_phone_number=_setting_or_environment(
                settings, "twilio/from_number", "TWILIO_FROM_PHONE_NUMBER"
            ),
            to_phone_number=_setting_or_environment(
                settings, "twilio/to_number", "TWILIO_TO_PHONE_NUMBER"
            ),
            message_body=_setting_or_environment(
                settings, "twilio/message_body", "TWILIO_SMS_BODY"
            ),
        )
        email = EmailConfig(
            smtp_host=_setting_or_environment(
                settings, "email/smtp_host", "SMTP_HOST"
            ),
            smtp_port=_integer_setting(settings, "email/smtp_port", "SMTP_PORT", 587),
            username=_setting_or_environment(
                settings, "email/username", "SMTP_USERNAME"
            ),
            password=smtp_password,
            sender_address=_setting_or_environment(
                settings, "email/sender_address", "EMAIL_FROM"
            ),
        )

        return cls(
            twilio=twilio,
            sms_enabled=_boolean_setting(
                settings, "notifications/sms_enabled", "SMS_ENABLED", False
            ),
            email_enabled=_boolean_setting(
                settings, "notifications/email_enabled", "EMAIL_ENABLED", False
            ),
            email_address=_setting_or_environment(
                settings, "notifications/email_address", "TO_EMAIL"
            ),
            email=email,
            desktop_notifications_enabled=_boolean_setting(
                settings,
                "notifications/desktop_enabled",
                "DESKTOP_NOTIFICATIONS_ENABLED",
                False,
            ),
            default_interval_seconds=_integer_setting(
                settings, "monitor/default_interval_seconds", "DEFAULT_INTERVAL_SECONDS", 300
            ),
        )
