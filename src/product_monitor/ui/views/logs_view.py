"""Live view of application log records."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
	QLabel,
	QPlainTextEdit,
	QVBoxLayout,
	QWidget,
)


class _QtLogHandler(QObject, logging.Handler):
	"""Forward application log records to the GUI thread."""

	record_emitted = pyqtSignal(object)

	def __init__(self) -> None:
		QObject.__init__(self)
		logging.Handler.__init__(self)

	def emit(self, record: logging.LogRecord) -> None:
		self.record_emitted.emit(record)


class LogsView(QWidget):
	"""Display recent application log records as timestamped lines."""

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._logger = logging.getLogger("product_monitor")
		self._logger.setLevel(min(self._logger.getEffectiveLevel(), logging.INFO))
		self._log_handler = _QtLogHandler()
		self._log_handler.setLevel(logging.DEBUG)
		self._log_handler.record_emitted.connect(self._add_record)
		self._logger.addHandler(self._log_handler)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(24, 24, 24, 24)
		layout.setSpacing(16)

		heading = QLabel(title)
		heading.setObjectName("pageHeading")
		layout.addWidget(heading)

		self.log_output = QPlainTextEdit()
		self.log_output.setObjectName("logOutput")
		self.log_output.setReadOnly(True)
		self.log_output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
		self.log_output.setMaximumBlockCount(500)
		self.log_output.setPlaceholderText("Application logs will appear here.")
		self.log_output.setFont(
			QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
		)
		layout.addWidget(self.log_output, 1)

	def _add_record(self, record: logging.LogRecord) -> None:
		timestamp = datetime.fromtimestamp(record.created).strftime(
			"%Y-%m-%d %H:%M:%S"
		)
		line = f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"
		if record.exc_info:
			line += "\n" + logging.Formatter().formatException(record.exc_info)
		self.log_output.appendPlainText(line)