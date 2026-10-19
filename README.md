# Product Availability Monitor

[![Tests](https://github.com/seal-000/product-availability-monitor/actions/workflows/tests.yml/badge.svg)](https://github.com/seal-000/product-availability-monitor/actions/workflows/tests.yml)

## 📋 Table of Contents

- [Project overview](#project-overview)
- [Features](#features)
- [Screenshots](#screenshots)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the app](#running-the-app)
- [Configuration](#configuration)
- [Testing](#testing)
- [Notes](#notes)

## Project overview

Product Availability Monitor is a desktop app for tracking whether a product is available on a retailer or product page and alerting you when availability changes.

It is built with Python, PyQt6, and Selenium, and it can monitor product pages, detect availability signals, and send desktop, SMS, or email notifications.

## Features

- Monitor one or more product pages for stock status
- Browser-based checks using Selenium
- Availability detection from storefront HTML content
- Configurable polling interval
- Desktop notifications
- Twilio SMS notifications
- SMTP email notifications
- Secure credential storage via the OS keyring
- Local app settings persisted with Qt settings

## Screenshots

### Dashboard

Add a product name and store URL, then start monitoring.

![Dashboard with the monitor table, create-monitor form, and notification status](docs/screenshots/dashboard.png)

### Settings

Configure the check interval and desktop, SMS, and email notifications.

![Settings page with notification and credential fields](docs/screenshots/settings.png)

### Logs

Review recent checks and results.

![Logs page showing a product check and its available result](docs/screenshots/logs.png)

### Desktop notification

Shown as a system tray toast when a monitored product becomes available.

![Windows desktop notification reporting a product is available](docs/screenshots/desktop-notification.png)

### Email notification

Sent through SMTP with the product name, page link, and stock evidence.

![Email alert reporting a product is available](docs/screenshots/email_notification.png)

## Project structure

- `src/product_monitor/` – application logic
- `src/product_monitor/ui/` – PyQt interface and widgets
- `tests/` – automated tests
- `docs/screenshots/` – README images
- `run_app.py` – application entry point

## Requirements

- Python 3.11+
- Chrome or Chromium installed with a matching ChromeDriver available to Selenium
- Optional: Twilio account and/or SMTP server for notifications

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

3. Install the project and test dependencies:

```bash
pip install -e .[test]
```

## Running the app

Start the desktop application with either of the following:

```bash
python run_app.py
```

or

```bash
python -m product_monitor.ui
```

## Configuration

You can configure the app in the UI under Settings.

The app also supports environment variables as fallbacks for notification settings, including:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE_NUMBER`
- `TWILIO_TO_PHONE_NUMBER`
- `TWILIO_SMS_BODY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `TO_EMAIL`
- `DEFAULT_INTERVAL_SECONDS`

Credentials entered in the app are stored in the operating system keyring when available.

## Testing

Run the test suite with:

```bash
pytest
```

## Notes

This project is designed for monitoring product availability on storefront pages and alerting you when items become available again. Check the code and tests for the precise product detection logic and notification behavior used by your specific setup.
