"""Deliver product availability alerts through configured channels."""

from __future__ import annotations

import base64
from email.message import EmailMessage
import json
import logging
import smtplib
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .config import AppConfig

logger = logging.getLogger(__name__)


class NotificationDeliveryError(RuntimeError):
    """Raised when a notification provider rejects or cannot deliver an alert."""


def _send_sms(config: AppConfig, subject: str, body: str) -> None:
    twilio = config.twilio
    account = quote(twilio.account_sid, safe="")
    endpoint = (
        f"https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json"
    )
    credentials = base64.b64encode(
        f"{twilio.account_sid}:{twilio.auth_token}".encode("utf-8")
    ).decode("ascii")
    request = Request(
        endpoint,
        data=urlencode(
            {
                "From": twilio.from_phone_number,
                "To": twilio.to_phone_number,
                "Body": twilio.message_body or f"{subject}\n{body}",
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15):
            return
    except HTTPError as error:
        try:
            response = json.loads(error.read().decode("utf-8"))
            provider_message = (
                response.get("message", str(error))
                if isinstance(response, dict)
                else str(error)
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            provider_message = str(error)
        raise NotificationDeliveryError(
            f"Twilio rejected the SMS: {provider_message}"
        ) from error
    except URLError as error:
        raise NotificationDeliveryError(
            f"Could not connect to Twilio: {error.reason}"
        ) from error


def _send_email(config: AppConfig, subject: str, body: str) -> None:
    email = config.email
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email.sender_address
    message["To"] = config.email_address
    message.set_content(body)

    if email.smtp_port == 465:
        with smtplib.SMTP_SSL(
            email.smtp_host,
            email.smtp_port,
            timeout=15,
            context=ssl.create_default_context(),
        ) as server:
            server.login(email.username, email.password)
            server.send_message(message)
        return

    with smtplib.SMTP(email.smtp_host, email.smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(email.username, email.password)
        server.send_message(message)


def send_availability_notifications(
    config: AppConfig,
    monitor_name: str,
    url: str,
    evidence: str | None,
) -> tuple[str, ...]:
    """Send enabled alerts and return explicit delivery errors, if any."""
    subject = f"Product available: {monitor_name}"
    body = (
        f"{monitor_name} appears to be available to order.\n"
        f"Page: {url}\n"
        f"Stock evidence: {evidence or '(none)'}"
    )
    errors = []

    if config.sms_enabled:
        if not config.twilio.is_configured:
            errors.append("SMS is enabled, but the Twilio settings are incomplete.")
        else:
            try:
                _send_sms(config, subject, body)
                logger.info("Sent availability SMS for monitor %s", monitor_name)
            except (
                NotificationDeliveryError,
                OSError,
                smtplib.SMTPException,
                ValueError,
            ) as error:
                errors.append(f"SMS delivery failed: {error}")
                logger.error(
                    "SMS delivery failed for monitor %s: %s", monitor_name, error
                )

    if config.email_enabled:
        if not config.email_address:
            errors.append("Email is enabled, but the recipient address is missing.")
        elif not config.email.is_configured:
            errors.append("Email is enabled, but the SMTP settings are incomplete.")
        else:
            try:
                _send_email(config, subject, body)
                logger.info("Sent availability email for monitor %s", monitor_name)
            except (OSError, smtplib.SMTPException, ValueError) as error:
                errors.append(f"Email delivery failed: {error}")
                logger.error(
                    "Email delivery failed for monitor %s: %s", monitor_name, error
                )

    return tuple(errors)
