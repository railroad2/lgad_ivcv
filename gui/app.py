import argparse
import os
import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def _parse_arguments(argv):
    parser = argparse.ArgumentParser(description="Launch the LGAD IV/CV GUI.")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_known_args(argv)


def _is_remote_session():
    return any(
        os.environ.get(name)
        for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")
    )


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    options, qt_arguments = _parse_arguments(arguments)
    if _is_remote_session() and not options.allow_remote:
        print(
            "LGAD IV/CV GUI execution is disabled in remote SSH sessions.",
            file=sys.stderr,
        )
        return 1

    qt_argv = [sys.argv[0], *qt_arguments]
    app = QApplication.instance() or QApplication(qt_argv)
    app.setApplicationName("LGAD IV/CV")
    app.setOrganizationName("LGAD")

    window = MainWindow()
    window.show()
    return app.exec()
