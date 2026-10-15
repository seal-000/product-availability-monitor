import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QHeaderView

from product_monitor.ui.components.monitor_table import MonitorTable


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_long_product_name_does_not_expand_table_past_viewport(qapp):
    table = MonitorTable()
    table.resize(700, 300)
    table.set_monitors(
        [
            {
                "name": "A very long product name " * 20,
                "url": "https://example.com/product",
                "interval": 300,
                "checked": "Not checked",
                "status": "Stopped",
                "result": "Waiting for first stock check",
            }
        ]
    )
    table.show()
    QApplication.processEvents()

    assert (
        table.horizontalHeader().sectionResizeMode(1)
        == QHeaderView.ResizeMode.Stretch
    )
    assert table.horizontalScrollBar().maximum() == 0
    table.close()
