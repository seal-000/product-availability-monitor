import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from appointment_monitor.ui.components.create_monitor_form import CreateMonitorForm


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_form_requires_a_product_name(qapp):
    form = CreateMonitorForm()
    emitted = []
    form.monitor_created.connect(emitted.append)
    form.url_input.setText("https://example.com/store/order")

    form._submit()

    assert emitted == []
    assert form.error_label.text() == "Enter the product you want to monitor."
    form.close()


def test_form_emits_product_and_store_page(qapp):
    form = CreateMonitorForm(default_interval_seconds=600)
    assert form.interval_combo.itemText(0) == "Default check interval"
    assert form.interval_combo.currentData() == 600
    emitted = []
    form.monitor_created.connect(emitted.append)
    form.product_input.setText("Original Glazed Dozen")
    form.url_input.setText("https://example.com/store/order")

    form._submit()

    assert emitted == [
        {
            "name": "Original Glazed Dozen",
            "product_name": "Original Glazed Dozen",
            "url": "https://example.com/store/order",
            "interval": 600,
            "status": "Running",
            "checked": "Just now",
            "result": "Stock status not checked yet",
        }
    ]
    assert form.product_input.text() == ""
    assert form.url_input.text() == ""
    form.close()


def test_form_default_interval_tracks_updated_setting(qapp):
    form = CreateMonitorForm(default_interval_seconds=600)

    form.set_default_interval(900)

    assert form.interval_combo.currentIndex() == 0
    assert form.interval_combo.currentData() == 900
    form.close()
