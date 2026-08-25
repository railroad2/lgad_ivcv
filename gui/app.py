import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("LGAD IV/CV")
    app.setOrganizationName("LGAD")

    window = MainWindow()
    window.show()
    return app.exec()
