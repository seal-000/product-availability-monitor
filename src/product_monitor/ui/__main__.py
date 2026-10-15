"""Run the product availability dashboard."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> int:
	"""Create and run the desktop application."""
	app = QApplication.instance() or QApplication(sys.argv)
	app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
	window = MainWindow()
	window.show()
	return app.exec()


if __name__ == "__main__":
	raise SystemExit(main())