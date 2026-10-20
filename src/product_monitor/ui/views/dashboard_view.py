"""Dashboard view for managing product availability monitors."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, pyqtSignal
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QStyle,
	QSystemTrayIcon,
	QVBoxLayout,
	QWidget,
)

from ...config import AppConfig, SETTINGS_APPLICATION, SETTINGS_ORGANIZATION
from ...detector import Availability, DetectorResult
from ...monitor import ProductMonitor
from ...notifications import send_availability_notifications
from ..components import CreateMonitorForm, MonitorTable, NotificationsInfo

logger = logging.getLogger(__name__)
MONITOR_RECORDS_KEY = "monitor/records"


class _CheckSignals(QObject):
	finished = pyqtSignal(str, object, object)


class _CheckWorker(QRunnable):
	def __init__(
		self,
		monitor_id: str,
		name: str,
		product_name: str,
		url: str,
		config: AppConfig,
		notify_on_available: bool,
	) -> None:
		super().__init__()
		self.monitor_id = monitor_id
		self.name = name
		self.product_name = product_name
		self.url = url
		self.config = config
		self.notify_on_available = notify_on_available
		self.signals = _CheckSignals()

	def run(self) -> None:
		monitor = ProductMonitor(self.url, self.product_name)
		try:
			result = monitor.check()
		except Exception as error:
			logger.exception("Unexpected monitor check failure for %s", self.url)
			result = DetectorResult(
				Availability.UNKNOWN,
				error_message=str(error).strip() or type(error).__name__,
			)
		finally:
			try:
				monitor.close()
			except Exception:
				logger.exception("Failed to close browser for %s", self.url)
		notification_errors: tuple[str, ...] = ()
		if (
			result.availability == Availability.AVAILABLE
			and self.notify_on_available
		):
			try:
				notification_errors = send_availability_notifications(
					self.config,
					self.name,
					self.url,
					result.evidence,
				)
			except Exception as error:
				logger.exception("Unexpected alert failure for %s", self.url)
				notification_errors = (
					f"Alert failed: {str(error).strip() or type(error).__name__}",
				)
		self.signals.finished.emit(
			self.monitor_id, result, notification_errors
		)


class DashboardView(QWidget):
	"""Show the product monitor table, create form, and notification info."""

	running_count_changed = pyqtSignal(int)

	def __init__(
		self,
		parent: QWidget | None = None,
		*,
		app_config: AppConfig | None = None,
	) -> None:
		"""Build the dashboard and load saved monitor definitions."""
		super().__init__(parent)
		self.app_config = app_config or AppConfig.load()
		self._settings = QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
		self._thread_pool = QThreadPool(self)
		self._thread_pool.setMaxThreadCount(3)
		self._timers: dict[str, QTimer] = {}
		self._checks_in_flight: set[str] = set()
		self._last_availability: dict[str, str] = {}
		self._tray_icon: QSystemTrayIcon | None = None
		self.monitors = self._load_monitors()
		self._build_ui()
		self._render_monitors()

	def _build_ui(self) -> None:
		"""Create the monitor table, action bar, form, and notification panel."""
		container_layout = QVBoxLayout(self)
		container_layout.setContentsMargins(0, 0, 0, 0)
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		scroll_area.setFrameShape(QFrame.Shape.NoFrame)
		scroll_area.setObjectName("dashboardScroll")
		content = QWidget()
		content.setObjectName("dashboardContent")
		scroll_area.setWidget(content)
		container_layout.addWidget(scroll_area)

		content_layout = QVBoxLayout(content)
		content_layout.setContentsMargins(24, 24, 24, 24)
		content_layout.setSpacing(16)

		heading_row = QHBoxLayout()
		heading = QLabel("Dashboard")
		heading.setObjectName("pageHeading")
		heading_row.addWidget(heading)
		heading_row.addStretch()
		self.summary_label = QLabel()
		self.summary_label.setObjectName("summaryLabel")
		heading_row.addWidget(self.summary_label)
		content_layout.addLayout(heading_row)

		subheading = QLabel(
			"Track a product on a store's ordering page and get notified when it can be ordered."
		)
		subheading.setObjectName("sectionSubheading")
		content_layout.addWidget(subheading)

		monitor_panel = QFrame(content)
		monitor_panel.setObjectName("panel")
		monitor_panel.setSizePolicy(
			QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
		)
		monitor_layout = QVBoxLayout(monitor_panel)
		monitor_layout.setContentsMargins(16, 14, 16, 14)
		monitor_layout.setSpacing(10)

		table_title = QLabel("MONITORED PRODUCTS")
		table_title.setObjectName("sectionLabel")
		monitor_layout.addWidget(table_title)

		self.table = MonitorTable(monitor_panel)
		monitor_layout.addWidget(self.table)
		action_row = QHBoxLayout()
		action_row.setContentsMargins(0, 12, 0, 0)
		action_row.setSpacing(6)
		self._add_action_button(action_row, "Remove", self._remove_selected)
		action_row.addStretch()
		self._add_action_button(
			action_row,
			"Start",
			lambda: self._set_selected_status("Running"),
		)
		self._add_action_button(
			action_row,
			"Stop",
			lambda: self._set_selected_status("Stopped"),
		)
		self._add_action_button(
			action_row,
			"Start All",
			lambda: self._set_all_status("Running"),
		)
		self._add_action_button(
			action_row,
			"Stop All",
			lambda: self._set_all_status("Stopped"),
		)
		monitor_layout.addLayout(action_row)
		content_layout.addWidget(monitor_panel)

		lower_row = QHBoxLayout()
		lower_row.setSpacing(16)
		self.create_monitor_form = CreateMonitorForm(
			default_interval_seconds=self.app_config.default_interval_seconds
		)
		self.create_monitor_form.monitor_created.connect(self._add_monitor)
		lower_row.addWidget(
			self.create_monitor_form,
			2,
			alignment=Qt.AlignmentFlag.AlignTop,
		)

		self.notifications_info = NotificationsInfo(app_config=self.app_config)
		lower_row.addWidget(
			self.notifications_info,
			1,
			alignment=Qt.AlignmentFlag.AlignTop,
		)
		content_layout.addLayout(lower_row, 1)

	def _add_action_button(
		self,
		layout: QHBoxLayout,
		text: str,
		callback: Any,
	) -> None:
		"""Add a compact action button."""
		button = QPushButton(text)
		button.setObjectName("monitorActionButton")
		button.clicked.connect(callback)
		layout.addWidget(button)

	def _render_monitors(self) -> None:
		"""Refresh table rows and the active-monitor summary."""
		self.table.set_monitors(self.monitors)
		running_count = len(self._timers)
		self.summary_label.setText(f"{running_count} RUNNING  /  {len(self.monitors)} TOTAL")
		self.running_count_changed.emit(running_count)

	def _set_selected_status(self, status: str) -> None:
		"""Start or stop checked monitors, or the focused row if none are checked."""
		rows = self.table.checked_rows()
		if not rows and self.table.currentRow() >= 0:
			rows = [self.table.currentRow()]
		for row in rows:
			if row >= len(self.monitors):
				continue
			monitor_id = self.monitors[row]["id"]
			if status == "Running":
				self._start_monitor(monitor_id)
			else:
				self._stop_monitor(monitor_id)

	def _add_monitor(self, monitor: dict[str, Any]) -> None:
		"""Save and start a monitor submitted by the create form."""
		record = monitor.copy()
		record["id"] = uuid.uuid4().hex
		record["product_name"] = str(record.get("product_name", "")).strip()
		record["name"] = record["product_name"] or str(record.get("name", "")).strip()
		record["status"] = "Stopped" if record["product_name"] else "Needs product"
		record["checked"] = "Not checked"
		record["result"] = (
			"Waiting for first stock check"
			if record["product_name"]
			else "Remove and recreate this old monitor with a product name"
		)
		self.monitors.append(record)
		self._save_monitors()
		self._start_monitor(record["id"])

	def _set_all_status(self, status: str) -> None:
		"""Start or stop every configured monitor."""
		for monitor in tuple(self.monitors):
			if status == "Running":
				self._start_monitor(monitor["id"])
			else:
				self._stop_monitor(monitor["id"])

	def _start_monitor(self, monitor_id: str) -> None:
		monitor = self._find_monitor(monitor_id)
		if monitor is None:
			return
		if not monitor.get("product_name"):
			monitor["status"] = "Needs product"
			monitor["result"] = (
				"Remove and recreate this old monitor with a product name"
			)
			self._render_monitors()
			return
		if monitor_id not in self._timers:
			timer = QTimer(self)
			timer.setInterval(max(1, int(monitor["interval"])) * 1000)
			timer.timeout.connect(
				lambda active_id=monitor_id: self._run_check(active_id)
			)
			self._timers[monitor_id] = timer
			timer.start()
		monitor["status"] = "Running"
		monitor["result"] = "Checking product stock..."
		self._render_monitors()
		self._run_check(monitor_id)

	def _stop_monitor(self, monitor_id: str) -> None:
		monitor = self._find_monitor(monitor_id)
		timer = self._timers.pop(monitor_id, None)
		if timer is not None:
			timer.stop()
			timer.deleteLater()
		if monitor is not None:
			monitor["status"] = "Stopped"
			monitor["result"] = "Monitoring stopped"
			logger.info("Stopped monitor %s (%s)", monitor["name"], monitor["url"])
		self._render_monitors()

	def _run_check(self, monitor_id: str) -> None:
		if monitor_id in self._checks_in_flight or monitor_id not in self._timers:
			return
		monitor = self._find_monitor(monitor_id)
		if monitor is None:
			return
		self._checks_in_flight.add(monitor_id)
		monitor["checked"] = "Checking..."
		monitor["result"] = "Checking product stock..."
		self._render_monitors()
		logger.info(
			"Checking product %s at %s", monitor["product_name"], monitor["url"]
		)
		worker = _CheckWorker(
			monitor_id,
			monitor["name"],
			monitor["product_name"],
			monitor["url"],
			self.app_config,
			self._last_availability.get(monitor_id) != Availability.AVAILABLE,
		)
		worker.signals.finished.connect(self._check_finished)
		self._thread_pool.start(worker)

	def _check_finished(
		self,
		monitor_id: str,
		result: DetectorResult,
		notification_errors: tuple[str, ...] = (),
	) -> None:
		self._checks_in_flight.discard(monitor_id)
		monitor = self._find_monitor(monitor_id)
		if monitor is None or monitor_id not in self._timers:
			return
		previously_available = (
			self._last_availability.get(monitor_id) == Availability.AVAILABLE
		)
		self._last_availability[monitor_id] = result.availability
		monitor["checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		if result.availability == Availability.AVAILABLE:
			monitor["status"] = "Running"
			monitor["result"] = f"Product available: {result.evidence or 'in stock'}"
			if not previously_available:
				self._show_desktop_notification(monitor["name"], result.evidence)
			if notification_errors:
				monitor["result"] += " | Alert issue: " + "; ".join(
					notification_errors
				)
				logger.error(
					"Alert delivery failed for monitor %s: %s",
					monitor["name"],
					"; ".join(notification_errors),
				)
		elif result.availability == Availability.UNAVAILABLE:
			monitor["status"] = "Running"
			monitor["result"] = (
				f"Product unavailable: {result.evidence or 'out of stock'}"
			)
		elif result.product_found:
			monitor["status"] = "Running"
			monitor["result"] = (
				"Product found, but stock status is unclear. Will keep checking."
			)
			logger.warning(
				"Monitor %s: %s", monitor["name"], result.error_message
			)
		else:
			monitor["status"] = "Error"
			monitor["result"] = result.error_message or "Could not determine availability"
		if result.availability == Availability.UNKNOWN and not result.product_found:
			logger.error(
				"Monitor %s could not determine availability: %s",
				monitor["name"],
				monitor["result"],
			)
		else:
			logger.info(
				"Monitor %s result: %s",
				monitor["name"],
				monitor["result"],
			)
		self._render_monitors()

	def _show_desktop_notification(self, name: str, evidence: str | None) -> None:
		"""Show a system tray toast when desktop notifications are enabled."""
		if not self.app_config.desktop_notifications_enabled:
			return
		if not QSystemTrayIcon.isSystemTrayAvailable():
			logger.warning("Desktop notifications are enabled, but no system tray exists")
			return
		if self._tray_icon is None:
			self._tray_icon = QSystemTrayIcon(
				self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),
				self,
			)
		self._tray_icon.show()
		self._tray_icon.showMessage(
			f"Product available: {name}",
			f"{name} appears to be available to order. ({evidence or 'in stock'})",
			QSystemTrayIcon.MessageIcon.Information,
			15000,
		)
		logger.info("Showed desktop notification for monitor %s", name)

	def _find_monitor(self, monitor_id: str) -> dict[str, Any] | None:
		return next(
			(monitor for monitor in self.monitors if monitor["id"] == monitor_id),
			None,
		)

	def _load_monitors(self) -> list[dict[str, Any]]:
		"""Load saved monitor definitions as stopped records."""
		raw_records = self._settings.value(MONITOR_RECORDS_KEY, "[]", type=str)
		try:
			saved_records = json.loads(raw_records)
		except (TypeError, ValueError):
			logger.warning("Ignoring invalid saved monitor records")
			return []
		if not isinstance(saved_records, list):
			return []

		records = []
		for saved in saved_records:
			if not isinstance(saved, dict) or not saved.get("name") or not saved.get("url"):
				continue
			product_name = str(saved.get("product_name", "")).strip()
			try:
				interval = max(1, int(saved["interval"]))
			except (KeyError, TypeError, ValueError):
				continue
			records.append(
				{
					"id": str(saved.get("id") or uuid.uuid4().hex),
					"name": product_name or str(saved["name"]),
					"product_name": product_name,
					"url": str(saved["url"]),
					"interval": interval,
					"status": "Stopped" if product_name else "Needs product",
					"checked": "Not checked",
					"result": (
						"Start monitoring to check product stock"
						if product_name
						else "Remove and recreate this old monitor with a product name"
					),
				}
			)
		return records

	def _save_monitors(self) -> None:
		"""Persist monitor definitions without transient run state."""
		saved_records = [
			{
				"id": monitor["id"],
				"name": monitor["name"],
				"product_name": monitor.get("product_name", ""),
				"url": monitor["url"],
				"interval": monitor["interval"],
			}
			for monitor in self.monitors
		]
		self._settings.setValue(MONITOR_RECORDS_KEY, json.dumps(saved_records))

	def update_config(self, app_config: AppConfig) -> None:
		"""Apply settings saved while the dashboard remains open."""
		self.app_config = app_config
		self.create_monitor_form.set_default_interval(
			app_config.default_interval_seconds
		)
		self.notifications_info.set_config(app_config)

	def shutdown(self) -> None:
		"""Stop scheduled checks and wait for active browser work to finish."""
		for timer in self._timers.values():
			timer.stop()
		self._timers.clear()
		self._thread_pool.waitForDone()
		if self._tray_icon is not None:
			self._tray_icon.hide()

	def _remove_selected(self) -> None:
		"""Remove checked monitors and stop their scheduled checks."""
		selected = set(self.table.checked_rows())
		for row in selected:
			if row < len(self.monitors):
				self._stop_monitor(self.monitors[row]["id"])
		self.monitors = [
			monitor for index, monitor in enumerate(self.monitors) if index not in selected
		]
		self._save_monitors()
		self._render_monitors()
