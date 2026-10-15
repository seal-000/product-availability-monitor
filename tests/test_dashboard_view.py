import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton

from product_monitor.config import AppConfig, TwilioConfig
from product_monitor.detector import Availability, DetectorResult
from product_monitor.ui.views import dashboard_view
from product_monitor.ui.views.dashboard_view import (
    MONITOR_RECORDS_KEY,
    DashboardView,
    _CheckWorker,
)


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.values[key] = value


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def create_config(interval=300):
    return AppConfig(
        twilio=TwilioConfig(),
        default_interval_seconds=interval,
    )


def create_view(monkeypatch, settings, config):
    monkeypatch.setattr(dashboard_view, "QSettings", lambda *_args: settings)
    return DashboardView(app_config=config)


def test_dashboard_loads_saved_monitors_stopped_and_uses_default_interval(
    monkeypatch, qapp
):
    settings = FakeSettings(
        {
            MONITOR_RECORDS_KEY: json.dumps(
                [
                    {
                        "id": "saved-monitor",
                        "name": "Original Glazed Dozen",
                        "product_name": "Original Glazed Dozen",
                        "url": "https://example.com/order",
                        "interval": 900,
                    }
                ]
            )
        }
    )
    view = create_view(monkeypatch, settings, create_config(interval=600))

    assert len(view.monitors) == 1
    assert view.monitors[0]["status"] == "Stopped"
    assert view.monitors[0]["id"] == "saved-monitor"
    assert view.create_monitor_form.interval_combo.currentData() == 600

    view.shutdown()
    view.close()


def test_legacy_monitor_without_product_name_is_not_started(monkeypatch, qapp):
    settings = FakeSettings(
        {
            MONITOR_RECORDS_KEY: json.dumps(
                [
                    {
                        "id": "legacy-monitor",
                        "name": "Old product monitor",
                        "url": "https://example.com/products",
                        "interval": 300,
                    }
                ]
            )
        }
    )
    view = create_view(monkeypatch, settings, create_config())

    view._start_monitor("legacy-monitor")

    assert view.monitors[0]["status"] == "Needs product"
    assert not view._timers
    assert "recreate" in view.monitors[0]["result"]
    view.shutdown()
    view.close()


def test_dashboard_add_starts_and_persists_monitor_then_stop_cancels_timer(
    monkeypatch, qapp
):
    settings = FakeSettings()
    view = create_view(monkeypatch, settings, create_config())
    monkeypatch.setattr(view, "_run_check", lambda _monitor_id: None)

    view._add_monitor(
        {
            "name": "Original Glazed Dozen",
            "product_name": "Original Glazed Dozen",
            "url": "https://example.com/order",
            "interval": 300,
        }
    )

    monitor = view.monitors[0]
    monitor_id = monitor["id"]
    assert monitor["status"] == "Running"
    assert view._timers[monitor_id].isActive()
    saved = json.loads(settings.values[MONITOR_RECORDS_KEY])[0]
    assert saved["name"] == "Original Glazed Dozen"
    assert saved["product_name"] == "Original Glazed Dozen"

    view._stop_monitor(monitor_id)

    assert monitor["status"] == "Stopped"
    assert monitor_id not in view._timers
    view.shutdown()
    view.close()


def test_unknown_result_sets_error_status_and_logs_at_error_level(
    monkeypatch, qapp, caplog
):
    settings = FakeSettings()
    view = create_view(monkeypatch, settings, create_config())
    monkeypatch.setattr(view, "_run_check", lambda _monitor_id: None)
    view._add_monitor(
        {
            "name": "Original Glazed Dozen",
            "product_name": "Original Glazed Dozen",
            "url": "https://example.com/order",
            "interval": 300,
        }
    )
    monitor = view.monitors[0]

    with caplog.at_level(
        "ERROR", logger="product_monitor.ui.views.dashboard_view"
    ):
        view._check_finished(
            monitor["id"],
            DetectorResult(
                Availability.UNKNOWN,
                error_message="This is not a service; avoid testing and monitoring.",
            ),
        )

    assert monitor["status"] == "Error"
    assert "could not determine availability" in caplog.text
    assert "avoid testing and monitoring" in caplog.text
    view.shutdown()
    view.close()


def test_check_worker_sends_alert_after_new_available_result(monkeypatch):
    config = create_config()
    results = []
    sent_alerts = []

    class FakeMonitor:
        def __init__(self, _url, product_name):
            assert product_name == "Original Glazed Dozen"

        def check(self):
            return DetectorResult(Availability.AVAILABLE, "active purchase button")

        def close(self):
            pass

    monkeypatch.setattr(dashboard_view, "ProductMonitor", FakeMonitor)
    monkeypatch.setattr(
        dashboard_view,
        "send_availability_notifications",
        lambda *args: sent_alerts.append(args) or (),
    )
    worker = _CheckWorker(
        "id",
        "Original Glazed Dozen",
        "Original Glazed Dozen",
        "https://example.com/order",
        config,
        notify_on_available=True,
    )
    worker.signals.finished.connect(
        lambda monitor_id, result, errors: results.append(
            (monitor_id, result, errors)
        )
    )

    worker.run()

    assert len(sent_alerts) == 1
    assert sent_alerts[0] == (
        config,
        "Original Glazed Dozen",
        "https://example.com/order",
        "active purchase button",
    )
    assert results[0][0] == "id"
    assert results[0][1].availability == Availability.AVAILABLE
    assert results[0][2] == ()


def test_check_worker_always_reports_when_alert_sending_crashes(monkeypatch):
    results = []

    class FakeMonitor:
        def __init__(self, _url, _product_name):
            pass

        def check(self):
            return DetectorResult(Availability.AVAILABLE, "in stock")

        def close(self):
            pass

    def crash(*_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(dashboard_view, "ProductMonitor", FakeMonitor)
    monkeypatch.setattr(dashboard_view, "send_availability_notifications", crash)
    worker = _CheckWorker(
        "id", "Item", "Item", "https://example.com", create_config(), True
    )
    worker.signals.finished.connect(lambda *args: results.append(args))

    worker.run()

    assert results[0][1].availability == Availability.AVAILABLE
    assert results[0][2] == ("Alert failed: boom",)


def test_available_monitor_displays_notification_delivery_failure(
    monkeypatch, qapp
):
    settings = FakeSettings()
    view = create_view(monkeypatch, settings, create_config())
    monkeypatch.setattr(view, "_run_check", lambda _monitor_id: None)
    view._add_monitor(
        {
            "name": "Original Glazed Dozen",
            "product_name": "Original Glazed Dozen",
            "url": "https://example.com/order",
            "interval": 300,
        }
    )
    monitor = view.monitors[0]

    view._check_finished(
        monitor["id"],
        DetectorResult(Availability.AVAILABLE, "active purchase button"),
        ("SMS delivery failed: Twilio rejected the SMS.",),
    )

    assert monitor["status"] == "Running"
    assert "SMS delivery failed" in monitor["result"]
    view.shutdown()
    view.close()


def test_compact_monitor_actions_stay_inside_the_table_panel(monkeypatch, qapp):
    view = create_view(monkeypatch, FakeSettings(), create_config())
    buttons = view.findChildren(QPushButton, "monitorActionButton")

    assert len(buttons) == 5
    assert all(button.parentWidget() is view.table.parentWidget() for button in buttons)
    assert [button.text() for button in buttons] == [
        "Remove",
        "Start",
        "Stop",
        "Start All",
        "Stop All",
    ]

    view.shutdown()
    view.close()


class FakeTray:
    instances = []

    def __init__(self, *_args):
        self.messages = []
        FakeTray.instances.append(self)

    @staticmethod
    def isSystemTrayAvailable():
        return True

    class MessageIcon:
        Information = 1

    def show(self):
        pass

    def hide(self):
        pass

    def showMessage(self, title, message, *_args):
        self.messages.append((title, message))


def _view_with_available_monitor(monkeypatch, desktop_enabled):
    FakeTray.instances = []
    monkeypatch.setattr(dashboard_view, "QSystemTrayIcon", FakeTray)
    config = create_config()
    config.desktop_notifications_enabled = desktop_enabled
    view = create_view(monkeypatch, FakeSettings(), config)
    monkeypatch.setattr(view, "_run_check", lambda _monitor_id: None)
    view._add_monitor(
        {
            "name": "Original Glazed Dozen",
            "product_name": "Original Glazed Dozen",
            "url": "https://example.com/order",
            "interval": 300,
        }
    )
    return view


def test_desktop_notification_shown_once_when_product_becomes_available(
    monkeypatch, qapp
):
    view = _view_with_available_monitor(monkeypatch, desktop_enabled=True)
    monitor_id = view.monitors[0]["id"]
    available = DetectorResult(Availability.AVAILABLE, "active purchase button")

    view._check_finished(monitor_id, available)
    view._check_finished(monitor_id, available)

    (tray,) = FakeTray.instances
    assert len(tray.messages) == 1
    assert "Original Glazed Dozen" in tray.messages[0][0]

    view._check_finished(
        monitor_id, DetectorResult(Availability.UNAVAILABLE, "sold out")
    )
    view._check_finished(monitor_id, available)
    assert len(tray.messages) == 2
    view.shutdown()
    view.close()


def test_desktop_notification_not_shown_when_disabled(monkeypatch, qapp):
    view = _view_with_available_monitor(monkeypatch, desktop_enabled=False)

    view._check_finished(
        view.monitors[0]["id"],
        DetectorResult(Availability.AVAILABLE, "active purchase button"),
    )

    assert FakeTray.instances == []
    view.shutdown()
    view.close()
