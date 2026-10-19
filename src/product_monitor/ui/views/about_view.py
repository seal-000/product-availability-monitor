"""About view with usage instructions and an overview of the app sections."""

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AboutView(QWidget):
	"""Explain how to set up monitors and notifications."""

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(24, 24, 24, 24)

		heading = QLabel(title)
		heading.setObjectName("pageHeading")
		layout.addWidget(heading)

		intro = QLabel(
			"Product Availability Monitor checks a named item on a store ordering page "
			"and can notify you when the item appears available to order."
		)
		intro.setObjectName("aboutIntro")
		intro.setWordWrap(True)
		intro.setMaximumWidth(900)
		layout.addWidget(intro)

		layout.addSpacing(12)
		setup_heading = QLabel("Required setup")
		setup_heading.setObjectName("aboutSectionTitle")
		layout.addWidget(setup_heading)

		setup_text = QLabel(
			"To add a product, enter its name and the store's online ordering URL. "
			"The monitor uses a separate browser, "
			"so location selections or sign-ins stored only in your regular browser "
			"may not carry over. The monitor looks for product "
			"stock data or purchase controls associated with that item; it does not "
			"treat unrelated page text as product availability. Pages without clear "
			"item-specific stock information are reported as unknown.\n\n"
			"For SMS alerts, you need an active Twilio account. In Settings, enter your "
			"Account SID, Auth Token, Twilio phone number, and alert recipient number "
			"in international format (for example +15551234567); then enable SMS and "
			"save. Twilio trial accounts can only text verified numbers, and US "
			"carriers may block messages from unregistered numbers. For email alerts, enter the recipient address, "
			"SMTP server, port, username, password, and sender address; "
			"then enable email and save. SMTP connections use STARTTLS, except port 465 "
			"which uses implicit TLS. Passwords are stored in the operating system "
			"credential store.\n\n"
			"During the current app session, alerts are sent when a monitor first "
			"detects availability. Repeated checks do not send duplicates while "
			"availability remains detected; an alert can be sent again after a later "
			"unavailable or unknown result."
		)
		setup_text.setObjectName("aboutBody")
		setup_text.setWordWrap(True)
		setup_text.setMaximumWidth(900)
		layout.addWidget(setup_text)

		layout.addSpacing(12)
		sections_heading = QLabel("Application sections")
		sections_heading.setObjectName("aboutSectionTitle")
		layout.addWidget(sections_heading)

		sections_text = QLabel(
			"Dashboard: manage product monitors.\n"
			"Settings: configure notification preferences.\n"
			"Logs: review recent application activity.\n"
			"About: setup instructions and an overview of the app."
		)
		sections_text.setObjectName("aboutBody")
		sections_text.setWordWrap(True)
		sections_text.setMaximumWidth(900)
		layout.addWidget(sections_text)
		layout.addStretch()