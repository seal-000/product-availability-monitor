"""Settings for product checks and notification integrations."""

import re

import keyring
from PyQt6.QtCore import QRegularExpression, QSettings, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
	QCheckBox,
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QScrollArea,
	QSizePolicy,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from ...config import AppConfig


class SettingsView(QWidget):
	"""Configure product-check intervals and notification preferences."""

	settings_saved = pyqtSignal(object)

	_SERVICE_NAME = "product-availability-monitor"
	_TOKEN_USERNAME = "twilio-auth-token"
	_SMTP_PASSWORD_USERNAME = "smtp-password"
	_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		settings = QSettings("Product Monitor", "Product Availability Monitor")

		container_layout = QVBoxLayout(self)
		container_layout.setContentsMargins(0, 0, 0, 0)
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		scroll_area.setFrameShape(QFrame.Shape.NoFrame)
		scroll_area.setObjectName("settingsScroll")
		content = QWidget()
		content.setObjectName("settingsContent")
		layout = QVBoxLayout(content)
		layout.setContentsMargins(24, 24, 24, 24)
		layout.setSpacing(16)

		heading = QLabel("Settings")
		heading.setObjectName("pageHeading")
		layout.addWidget(heading)

		monitoring_heading = QLabel("Product monitoring")
		monitoring_heading.setObjectName("notificationTitle")
		layout.addWidget(monitoring_heading)

		monitoring_form = QFormLayout()
		monitoring_form.setHorizontalSpacing(16)
		monitoring_form.setVerticalSpacing(24)
		self.default_interval = QSpinBox()
		self.default_interval.setRange(15, 86400)
		self.default_interval.setSuffix(" seconds")
		self.default_interval.setValue(
			settings.value("monitor/default_interval_seconds", 300, type=int)
		)
		monitoring_form.addRow("Default check interval", self.default_interval)
		layout.addLayout(monitoring_form)

		self.desktop_enabled = QCheckBox("Enable desktop notifications")
		self.desktop_enabled.setChecked(
			settings.value("notifications/desktop_enabled", False, type=bool)
		)
		layout.addWidget(self.desktop_enabled)

		section_heading = QLabel("Twilio SMS")
		section_heading.setObjectName("notificationTitle")
		layout.addWidget(section_heading)

		description = QLabel(
			"Enter your Twilio account details and the phone numbers for SMS alerts."
		)
		layout.addWidget(description)

		self.sms_enabled = QCheckBox("Enable phone (SMS) notifications")
		self.sms_enabled.setChecked(
			settings.value("notifications/sms_enabled", False, type=bool)
		)
		layout.addWidget(self.sms_enabled)
		self.email_enabled = QCheckBox("Enable email notifications")
		self.email_enabled.setChecked(
			settings.value("notifications/email_enabled", False, type=bool)
		)
		layout.addWidget(self.email_enabled)

		form = QFormLayout()
		form.setHorizontalSpacing(16)
		form.setVerticalSpacing(24)
		self.account_sid = QLineEdit(settings.value("twilio/account_sid", ""))
		self.account_sid.setPlaceholderText("AC...")
		form.addRow("Account SID", self.account_sid)

		self.auth_token = QLineEdit()
		self.auth_token.setEchoMode(QLineEdit.EchoMode.Password)
		self.auth_token.setPlaceholderText("Twilio Auth Token")
		try:
			self.auth_token.setText(
				keyring.get_password(self._SERVICE_NAME, self._TOKEN_USERNAME) or ""
			)
		except keyring.errors.KeyringError:
			pass
		form.addRow("Auth Token", self.auth_token)

		self.from_number = QLineEdit(settings.value("twilio/from_number", ""))
		self.from_number.setPlaceholderText("+15551234567")
		form.addRow("Twilio phone number", self.from_number)

		self.to_number = QLineEdit(settings.value("twilio/to_number", ""))
		self.to_number.setPlaceholderText("+15557654321")
		form.addRow("Alert recipient", self.to_number)

		self.sms_message = QLineEdit(settings.value("twilio/message_body", ""))
		self.sms_message.setPlaceholderText(
			"Optional; trial accounts: sms_product_reminders"
		)
		form.addRow("SMS message text", self.sms_message)

		self.email_address = QLineEdit(
			settings.value("notifications/email_address", "")
		)
		self.email_address.setPlaceholderText("your@email.com")
		self.email_address.setValidator(
			QRegularExpressionValidator(
				QRegularExpression(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
			)
		)
		form.addRow("Alert recipient email", self.email_address)
		self.smtp_host = QLineEdit(settings.value("email/smtp_host", ""))
		self.smtp_host.setPlaceholderText("smtp.example.com")
		form.addRow("SMTP server", self.smtp_host)
		self.smtp_port = QSpinBox()
		self.smtp_port.setRange(1, 65535)
		self.smtp_port.setValue(settings.value("email/smtp_port", 587, type=int))
		form.addRow("SMTP port (465 for SSL, otherwise STARTTLS)", self.smtp_port)
		self.smtp_username = QLineEdit(settings.value("email/username", ""))
		self.smtp_username.setPlaceholderText("Your SMTP account username")
		form.addRow("SMTP username", self.smtp_username)
		self.smtp_password = QLineEdit()
		self.smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
		self.smtp_password.setPlaceholderText("SMTP account password or app password")
		try:
			self.smtp_password.setText(
				keyring.get_password(
					self._SERVICE_NAME, self._SMTP_PASSWORD_USERNAME
				) or ""
			)
		except keyring.errors.KeyringError:
			pass
		form.addRow("SMTP password", self.smtp_password)
		self.email_sender = QLineEdit(settings.value("email/sender_address", ""))
		self.email_sender.setPlaceholderText("sender@example.com")
		self.email_sender.setValidator(
			QRegularExpressionValidator(
				QRegularExpression(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
			)
		)
		form.addRow("Email sender address", self.email_sender)
		layout.addLayout(form)

		# A fixed height keeps the form from squeezing the row spacing away
		# when the window is short.
		for field in (self.default_interval, *content.findChildren(QLineEdit),
			self.smtp_port):
			field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

		actions = QHBoxLayout()
		self.save_button = QPushButton("Save settings")
		self.save_button.setObjectName("startMonitoringButton")
		self.save_button.clicked.connect(self._save_settings)
		actions.addWidget(self.save_button)
		self.status = QLabel("")
		self.status.setObjectName("settingsStatus")
		actions.addWidget(self.status, 1)
		layout.addLayout(actions)
		layout.addStretch()
		scroll_area.setWidget(content)
		container_layout.addWidget(scroll_area)

	def _save_settings(self) -> None:
		"""Persist notification settings and store credentials in the OS keyring."""
		account_sid = self.account_sid.text().strip()
		auth_token = self.auth_token.text().strip()
		from_number = self.from_number.text().strip()
		to_number = self.to_number.text().strip()
		sms_message = self.sms_message.text().strip()
		email_address = self.email_address.text().strip()
		smtp_host = self.smtp_host.text().strip()
		smtp_username = self.smtp_username.text().strip()
		smtp_password = self.smtp_password.text().strip()
		email_sender = self.email_sender.text().strip()
		# An incomplete channel is saved as disabled instead of blocking the
		# whole save, so changes to other channels still take effect.
		problems = []
		sms_enabled = self.sms_enabled.isChecked()
		email_enabled = self.email_enabled.isChecked()
		if sms_enabled and not all(
			(account_sid, auth_token, from_number, to_number)
		):
			sms_enabled = False
			problems.append("SMS not enabled: complete all four Twilio fields.")
		if email_enabled:
			if not self._EMAIL_PATTERN.fullmatch(email_address):
				problem = "enter a valid alert recipient email address."
			elif not all((smtp_host, smtp_username, smtp_password, email_sender)):
				problem = "complete all SMTP fields."
			elif not self._EMAIL_PATTERN.fullmatch(email_sender):
				problem = "enter a valid email sender address."
			else:
				problem = ""
			if problem:
				email_enabled = False
				problems.append(f"Email not enabled: {problem}")

		try:
			if auth_token:
				keyring.set_password(
					self._SERVICE_NAME, self._TOKEN_USERNAME, auth_token
				)
			if smtp_password:
				keyring.set_password(
					self._SERVICE_NAME,
					self._SMTP_PASSWORD_USERNAME,
					smtp_password,
				)
		except keyring.errors.KeyringError:
			self.status.setText("Could not access the system credential store.")
			return

		settings = QSettings("Product Monitor", "Product Availability Monitor")
		settings.setValue("notifications/sms_enabled", sms_enabled)
		settings.setValue("notifications/email_enabled", email_enabled)
		settings.setValue(
			"notifications/desktop_enabled", self.desktop_enabled.isChecked()
		)
		settings.setValue("twilio/account_sid", account_sid)
		settings.setValue("twilio/from_number", from_number)
		settings.setValue("twilio/to_number", to_number)
		settings.setValue("twilio/message_body", sms_message)
		settings.setValue("notifications/email_address", email_address)
		settings.setValue("email/smtp_host", smtp_host)
		settings.setValue("email/smtp_port", self.smtp_port.value())
		settings.setValue("email/username", smtp_username)
		settings.setValue("email/sender_address", email_sender)
		settings.setValue(
			"monitor/default_interval_seconds", self.default_interval.value()
		)
		self.status.setText(
			"Settings saved. " + " ".join(problems) if problems else "Settings saved."
		)
		self.settings_saved.emit(AppConfig.load())
