import sys

from PySide6.QtWidgets import QApplication

from epic_trips_crm.app.window import MainWindow


def test_main_window_instantiates():
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow()
    assert w.windowTitle()