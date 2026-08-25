from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QToolButton, QWidget


class ChannelGrid(QWidget):
    """A 16 by 16 selector that exposes linear switch channel numbers."""

    selection_changed = Signal(int)
    CELL_SIZE = 26

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QToolButton, QPushButton { padding: 0; font-size: 9px; }"
            "QToolButton:checked { background-color: #2878b5; color: white; }"
        )
        self._buttons = []
        self._row_headers = []
        self._col_headers = []
        self._selection_mode = "channel"

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(1)
        layout.setVerticalSpacing(1)

        corner = QPushButton("R/C")
        corner.setEnabled(False)
        corner.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
        layout.addWidget(corner, 0, 0)

        for col in range(16):
            button = QPushButton(f"{col:02d}")
            button.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
            button.clicked.connect(lambda _checked=False, c=col: self.toggle_col(c))
            layout.addWidget(button, 0, col + 1)
            self._col_headers.append(button)

        for row in range(16):
            row_label = chr(ord("A") + row)
            header = QPushButton(row_label)
            header.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
            header.clicked.connect(lambda _checked=False, r=row: self.toggle_row(r))
            layout.addWidget(header, row + 1, 0)
            self._row_headers.append(header)

            row_buttons = []
            for col in range(16):
                channel = row * 16 + col
                button = QToolButton()
                button.setText(str(channel))
                button.setCheckable(True)
                button.setChecked(True)
                button.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
                button.toggled.connect(
                    lambda checked, r=row, c=col: self._button_toggled(
                        r, c, checked
                    )
                )
                button.setToolTip(
                    f"row {row_label}, column {col:02d}, channel {channel}"
                )
                layout.addWidget(button, row + 1, col + 1)
                row_buttons.append(button)
            self._buttons.append(row_buttons)

    def _selection_changed(self, _checked=False):
        self.selection_changed.emit(len(self.selected_targets()))

    def _button_toggled(self, row, col, checked):
        if self._selection_mode == "row":
            self._set_buttons(self._buttons[row], checked)
        elif self._selection_mode == "column":
            self._set_buttons([buttons[col] for buttons in self._buttons], checked)
        else:
            self._selection_changed()

    def set_selection_mode(self, mode):
        if mode not in ("channel", "row", "column"):
            raise ValueError(f"Unknown channel selection mode: {mode}")

        self._selection_mode = mode
        for header in self._row_headers:
            header.setEnabled(mode != "column")
        for header in self._col_headers:
            header.setEnabled(mode != "row")

        if mode == "row":
            selected_rows = set(self.selected_rows())
            for row, buttons in enumerate(self._buttons):
                self._set_buttons(buttons, row in selected_rows, emit=False)
        elif mode == "column":
            selected_cols = set(self.selected_columns())
            for col in range(16):
                self._set_buttons(
                    [buttons[col] for buttons in self._buttons],
                    col in selected_cols,
                    emit=False,
                )
        self._selection_changed()

    def selected_channels(self):
        return [
            row * 16 + col
            for row, buttons in enumerate(self._buttons)
            for col, button in enumerate(buttons)
            if button.isChecked()
        ]

    def selected_rows(self):
        return [
            row
            for row, buttons in enumerate(self._buttons)
            if any(button.isChecked() for button in buttons)
        ]

    def selected_columns(self):
        return [
            col
            for col in range(16)
            if any(self._buttons[row][col].isChecked() for row in range(16))
        ]

    def selected_targets(self):
        if self._selection_mode == "row":
            return self.selected_rows()
        if self._selection_mode == "column":
            return self.selected_columns()
        return self.selected_channels()

    def _set_buttons(self, buttons, checked, emit=True):
        for button in buttons:
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
        if emit:
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
