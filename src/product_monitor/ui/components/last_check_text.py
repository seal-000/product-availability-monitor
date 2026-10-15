"""Text shown for a monitor's most recent check result."""

from PyQt6.QtWidgets import QLabel, QWidget


class LastCheckText(QLabel):
	"""Format a monitor state as a concise last-check message."""

	def __init__(
		self,
		status: str,
		name: str,
		result: str,
		parent: QWidget | None = None,
	) -> None:
		message = self.message_for(status, name, result)
		super().__init__(message, parent)
		self.setObjectName("lastCheckText")
		self.setProperty("variant", "error" if status == "Error" else "default")
		self.setToolTip(message)

	@staticmethod
	def message_for(status: str, name: str, result: str = "") -> str:
		if status == "Running":
			return result or "Monitor is running"
		if status == "Available":
			return f"{name} is available"
		if status == "Stopped":
			return "Monitor has been stopped"
		if status == "Error":
			return result or "Error"
		return result or status
