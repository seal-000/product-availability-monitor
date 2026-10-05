"""Navigation sidebar for the product monitor dashboard."""

from pathlib import Path

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout


class Sidebar(QFrame):
	"""Render the app navigation and emit the selected destination."""

	navigation_requested = pyqtSignal(str)

	def __init__(self, parent=None) -> None:
		"""Create the branded sidebar with icon buttons and app status."""
		super().__init__(parent)
		self.setObjectName("sidebar")
		self.setFixedWidth(206)
		self.nav_buttons: dict[str, QPushButton] = {}
		self._button_group = QButtonGroup(self)
		self._button_group.setExclusive(True)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(18, 22, 18, 16)
		layout.setSpacing(4)

		brand = QLabel("MONITOR APP")
		brand.setObjectName("brand")
		layout.addWidget(brand)
		layout.addSpacing(22)

		icons_dir = Path(__file__).parents[1] / "resources" / "imgs"
		navigation_items = (
			("Dashboard", "home-icon.svg", "Open dashboard"),
			("Settings", "settings-icon.svg", "Open settings"),
			("Logs", "logs-icon.svg", "View monitor logs"),
			("About", "info-icon.svg", "About this application"),
		)
		for name, icon_file, tooltip in navigation_items:
			button = QPushButton(name)
			button.setObjectName("navButton")
			button.setCheckable(True)
			button.setToolTip(tooltip)
			button.setAccessibleName(name)
			button.setIcon(QIcon(str(icons_dir / icon_file)))
			button.setIconSize(QSize(18, 18))
			button.clicked.connect(
				lambda checked=False, page=name: self.navigation_requested.emit(page)
			)
			self._button_group.addButton(button)
			self.nav_buttons[name] = button
			layout.addWidget(button)

		self.nav_buttons["Dashboard"].setChecked(True)
		layout.addStretch()

		app_status = QLabel("●  Demo data loaded")
		app_status.setObjectName("sidebarStatus")
		layout.addWidget(app_status)
		version = QLabel("PRODUCT MONITOR  ·  0.1.0")
		version.setObjectName("versionLabel")
		layout.addWidget(version)

	def set_active_page(self, name: str) -> None:
		"""Select a navigation item by its displayed name."""
		button = self.nav_buttons.get(name)
		if button is not None:
			button.setChecked(True)