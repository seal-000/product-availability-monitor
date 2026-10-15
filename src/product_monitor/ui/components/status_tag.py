"""Compact reusable status badge for UI components."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget


class StatusTag(QLabel):
	"""Display a short status in a compact, non-stretching pill."""

	def __init__(
		self,
		text: str,
		variant: str = "success",
		parent: QWidget | None = None,
	) -> None:
		"""Create a centered status tag with the requested visual variant."""
		super().__init__(text, parent)
		self.setObjectName("statusTag")
		self.setProperty("variant", variant)
		self.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
		self.setFixedHeight(28)