"""Notification channels and their enabled states."""

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
	QFrame,
	QHBoxLayout,
	QLabel,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from ...config import AppConfig
from .notification_channel import NotificationChannel
from .status_tag import StatusTag


class NotificationsInfo(QFrame):
	"""Show configured notification channels and enabled indicators."""

	def __init__(
		self,
		parent: QWidget | None = None,
		*,
		app_config: AppConfig | None = None,
	) -> None:
		"""Build the notification summary card using the supplied SVG assets."""
		super().__init__(parent)
		self.app_config = app_config or AppConfig.load()
		self.setObjectName("panel")
		self.setSizePolicy(
			QSizePolicy.Policy.Expanding,
			QSizePolicy.Policy.Maximum,
		)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 14, 16, 16)
		layout.setSpacing(10)

		icons_dir = Path(__file__).parents[1] / "resources" / "imgs"
		heading = QHBoxLayout()
		heading.setSpacing(10)
		heading.addWidget(
			self._icon_tile(icons_dir / "notifications_icon.svg", "notificationHeaderIcon")
		)

		title = QLabel("Notifications")
		title.setObjectName("notificationTitle")
		heading.addWidget(title)
		heading.addStretch()

		self.enabled_badge = StatusTag("Not configured", "neutral")
		heading.addWidget(self.enabled_badge)
		layout.addLayout(heading)

		layout.addSpacing(4)
		self.email_channel = NotificationChannel(
			"Email",
			"Not configured",
			(icons_dir / "alternate_email_icon.svg",),
			enabled=False,
		)
		layout.addWidget(self.email_channel)
		self.sms_channel = NotificationChannel(
			"SMS",
			"Not configured",
			(icons_dir / "sms_enabled_icon.svg",),
			enabled=False,
		)
		layout.addWidget(self.sms_channel)
		self.set_config(self.app_config)

	def set_config(self, app_config: AppConfig) -> None:
		"""Refresh channel contacts and enabled states from saved preferences."""
		self.app_config = app_config
		email_ready = (
			app_config.email_enabled
			and bool(app_config.email_address)
			and app_config.email.is_configured
		)
		sms_ready = app_config.sms_enabled and app_config.twilio.is_configured
		self.email_channel.set_state(
			app_config.email_address or "Not configured", email_ready
		)
		self.sms_channel.set_state(
			app_config.twilio.to_phone_number or "Not configured", sms_ready
		)
		configured = app_config.has_configured_notification
		self.enabled_badge.setText("Configured" if configured else "Not configured")
		self.enabled_badge.setProperty(
			"variant", "success" if configured else "neutral"
		)
		self.enabled_badge.style().unpolish(self.enabled_badge)
		self.enabled_badge.style().polish(self.enabled_badge)

	@staticmethod
	def _icon_tile(icon_source: Path | str, object_name: str) -> QLabel:
		"""Create a consistent icon tile from an SVG path or short text symbol."""
		icon = QLabel()
		icon.setObjectName(object_name)
		icon.setFixedSize(32, 32)
		icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
		if isinstance(icon_source, Path):
			icon.setPixmap(QIcon(str(icon_source)).pixmap(QSize(18, 18)))
		else:
			icon.setText(icon_source)
		return icon
