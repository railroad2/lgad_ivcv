from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QToolButton, QWidget


class ChannelGrid(QWidget):
    """A 16 by 16 selector that exposes linear switch channel numbers."""

    selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QToolButton:checked { background-color: #2878b5; color: white; }"
        )
        self._buttons = []

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(2)
        layout.setVerticalSpacing(2)

        corner = QPushButton("R/C")
        corner.setEnabled(False)
        corner.setFixedSize(42, 28)
        layout.addWidget(corner, 0, 0)

        for col in range(16):
            button = QPushButton(f"C{col}")
            button.setFixedSize(38, 28)
            button.clicked.connect(lambda _checked=False, c=col: self.toggle_col(c))
            layout.addWidget(button, 0, col + 1)

        for row in range(16):
            header = QPushButton(f"R{row}")
            header.setFixedSize(42, 28)
            header.clicked.connect(lambda _checked=False, r=row: self.toggle_row(r))
            layout.addWidget(header, row + 1, 0)

            row_buttons = []
            for col in range(16):
                channel = row * 16 + col
                button = QToolButton()
                button.setText(str(channel))
                button.setCheckable(True)
                button.setChecked(True)
                button.setFixedSize(38, 28)
                button.toggled.connect(self._selection_changed)
                button.setToolTip(f"row {row}, column {col}, channel {channel}")
                layout.addWidget(button, row + 1, col + 1)
                row_buttons.append(button)
            self._buttons.append(row_buttons)

    def _selection_changed(self, _checked=False):
        self.selection_changed.emit(len(self.selected_channels()))

    def selected_channels(self):
        return [
            row * 16 + col
            for row, buttons in enumerate(self._buttons)
            for col, button in enumerate(buttons)
            if button.isChecked()
        ]

    def _set_buttons(self, buttons, checked):
        for button in buttons:
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
        self._selection_changed()

    def select_all(self):
        self._set_buttons(
            [button for row in self._buttons for button in row],
            True,
        )

    def clear_all(self):
        self._set_buttons(
            [button for row in self._buttons for button in row],
            False,
        )

    def toggle_row(self, row):
        buttons = self._buttons[row]
        self._set_buttons(buttons, not all(button.isChecked() for button in buttons))

    def toggle_col(self, col):
        buttons = [row[col] for row in self._buttons]
        self._set_buttons(buttons, not all(button.isChecked() for button in buttons))
