import sys

from PySide6.QtWidgets import QApplication

from epic_trips_crm.app.widgets.config_status import ConfigStatus


def test_config_status_instantiates():
    _ = QApplication.instance() or QApplication(sys.argv)
    w = ConfigStatus()
    assert w is not None
