"""Form for adding a product and store ordering page to the monitor list."""

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
	QComboBox,
	QFrame,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QSizePolicy,
	QVBoxLayout,
)


class CreateMonitorForm(QFrame):
	"""Collect product monitor details and emit a validated monitor record."""

	monitor_created = pyqtSignal(dict)

	def __init__(
		self,
		parent=None,
		default_interval_seconds: int = 300,
	) -> None:
		"""Build the product, store URL, interval, and start-monitoring controls."""
		super().__init__(parent)
		self.setObjectName("panel")
		self.setSizePolicy(
			QSizePolicy.Policy.Expanding,
			QSizePolicy.Policy.Maximum,
		)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 14, 16, 16)
		layout.setSpacing(8)

		title = QLabel("CREATE MONITOR")
		title.setObjectName("sectionLabel")
		layout.addWidget(title)

		self.product_input = self._add_text_field(
			layout,
			"Product",
			"e.g. Original Glazed dozen",
		)
		self.url_input = self._add_text_field(
			layout,
			"Store ordering page URL",
			"https://example.com/order",
		)
		instructions = QLabel(
			"Use a store-specific ordering URL. Availability is determined from the "
			"matching product's stock data or order controls; a location selected only "
			"in your regular browser may not carry over."
		)
		instructions.setWordWrap(True)
		layout.addWidget(instructions)

		bottom_row = QHBoxLayout()
		bottom_row.setSpacing(12)

		interval_column = QVBoxLayout()
		interval_column.setSpacing(5)
		interval_label = QLabel("Check interval")
		interval_label.setObjectName("formLabel")
		interval_column.addWidget(interval_label)
		self.interval_combo = QComboBox()
		self.interval_combo.addItem(
			"Default",
			default_interval_seconds,
		)
		intervals = (5 * 60, 10 * 60, 15 * 60, 30 * 60)
		for interval in intervals:
			self.interval_combo.addItem(f"{interval // 60} minutes", interval)
		self.interval_combo.setCurrentIndex(0)
		interval_column.addWidget(self.interval_combo)
		bottom_row.addLayout(interval_column, 1)

		self.start_button = QPushButton("Start Monitoring")
		self.start_button.setObjectName("startMonitoringButton")
		play_icon = Path(__file__).parents[1] / "resources" / "imgs" / "play-arrow-icon.svg"
		self.start_button.setIcon(QIcon(str(play_icon)))
		self.start_button.setIconSize(QSize(18, 18))
		self.start_button.setMinimumHeight(44)
		self.start_button.clicked.connect(self._submit)
		bottom_row.addWidget(
			self.start_button,
			2,
			alignment=Qt.AlignmentFlag.AlignBottom,
		)
		layout.addLayout(bottom_row)

		self.error_label = QLabel()
		self.error_label.setObjectName("formError")
		self.error_label.setWordWrap(True)
		layout.addWidget(self.error_label)

	def set_default_interval(self, interval_seconds: int) -> None:
		"""Update and select the configured default interval."""
		self.interval_combo.setItemData(0, interval_seconds)
		self.interval_combo.setCurrentIndex(0)

	@staticmethod
	def _add_text_field(layout: QVBoxLayout, label_text: str, placeholder: str) -> QLineEdit:
		"""Add a labeled single-line text input and return the input widget."""
		label = QLabel(label_text)
		label.setObjectName("formLabel")
		layout.addWidget(label)
		field = QLineEdit()
		field.setObjectName("formInput")
		field.setPlaceholderText(placeholder)
		field.setClearButtonEnabled(True)
		layout.addWidget(field)
		return field

	def _submit(self) -> None:
		"""Validate the entered product details and emit a monitor record."""
		product_name = self.product_input.text().strip()
		url_text = self.url_input.text().strip()
		url = QUrl(url_text)

		if not product_name:
			self.error_label.setText("Enter the product you want to monitor.")
			self.product_input.setFocus()
			return
		if url.scheme().lower() not in ("http", "https") or not url.host():
			self.error_label.setText("Enter a valid HTTP or HTTPS URL.")
			self.url_input.setFocus()
			return

		self.error_label.clear()
		self.monitor_created.emit(
			{
				"name": product_name,
				"product_name": product_name,
				"url": url.toString(),
				"interval": int(self.interval_combo.currentData()),
				"status": "Running",
				"checked": "Just now",
				"result": "Stock status not checked yet",
			}
		)
		self.product_input.clear()
		self.url_input.clear()