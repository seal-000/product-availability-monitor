from urllib.parse import parse_qs

from appointment_monitor.config import AppConfig, EmailConfig, TwilioConfig
from appointment_monitor.notifications import send_availability_notifications
from appointment_monitor import notifications


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_sms_posts_twilio_message(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(notifications, "urlopen", fake_urlopen)
    config = AppConfig(
        twilio=TwilioConfig(
            account_sid="AC123",
            auth_token="token",
            from_phone_number="+15550000001",
            to_phone_number="+15550000002",
        ),
        sms_enabled=True,
    )

    errors = send_availability_notifications(
        config, "Clinic", "https://example.com", "appointments available"
    )

    request = captured["request"]
    payload = parse_qs(request.data.decode("utf-8"))
    assert errors == ()
    assert request.full_url.endswith("/Accounts/AC123/Messages.json")
    assert payload["From"] == ["+15550000001"]
    assert payload["To"] == ["+15550000002"]
    assert "appointments available" in payload["Body"][0]
    assert captured["timeout"] == 15


def test_sms_uses_configured_message_body(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return FakeResponse()

    monkeypatch.setattr(notifications, "urlopen", fake_urlopen)
    config = AppConfig(
        twilio=TwilioConfig(
            account_sid="AC123",
            auth_token="token",
            from_phone_number="+15550000001",
            to_phone_number="+15550000002",
            message_body="sms_appointment_reminders",
        ),
        sms_enabled=True,
    )

    errors = send_availability_notifications(
        config, "Clinic", "https://example.com", "open slot"
    )

    payload = parse_qs(captured["request"].data.decode("utf-8"))
    assert errors == ()
    assert payload["Body"] == ["sms_appointment_reminders"]


def test_email_sends_message_using_starttls(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, context):
            calls.append(("starttls", context))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)
    config = AppConfig(
        twilio=TwilioConfig(),
        email_enabled=True,
        email_address="recipient@example.com",
        email=EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="smtp-user",
            password="smtp-secret",
            sender_address="sender@example.com",
        ),
    )

    errors = send_availability_notifications(
        config, "Clinic", "https://example.com", "open slot"
    )

    assert errors == ()
    assert calls[0] == ("connect", "smtp.example.com", 587, 15)
    assert calls.count(("ehlo",)) == 2
    assert calls[2][0] == "starttls"
    assert ("login", "smtp-user", "smtp-secret") in calls
    assert (
        "send",
        "recipient@example.com",
        "Product available: Clinic",
    ) in calls


def test_enabled_incomplete_channel_returns_visible_error():
    config = AppConfig(
        twilio=TwilioConfig(),
        sms_enabled=True,
        email_enabled=True,
        email_address="recipient@example.com",
    )

    errors = send_availability_notifications(config, "Clinic", "https://example.com", None)

    assert errors == (
        "SMS is enabled, but the Twilio settings are incomplete.",
        "Email is enabled, but the SMTP settings are incomplete.",
    )
