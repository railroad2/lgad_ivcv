from collections.abc import Iterable
from typing import Optional, Union

try:
    from swm_ctrl.websocket_client import (
        PinInput,
        WebSocketClientSync,
    )
except ModuleNotFoundError as exc:
    if exc.name == "swm_ctrl":
        raise ModuleNotFoundError(
            "GateComm requires the swm_ctrl package. "
            "Install swm_ctrl or add its parent directory to PYTHONPATH."
        ) from exc
    raise


PinCollection = Union[PinInput, Iterable[PinInput]]


class GateComm(WebSocketClientSync):
    """SWmat compatibility layer over swm_ctrl.WebSocketClientSync."""

    def __init__(
        self,
        uri: Optional[str] = None,
        timeout: float = 5.0,
        connect_timeout: float = 5.0,
    ):
        # The gateway assigns roles by port:
        #   8765 -> control, 8766 -> monitor
        # No URL path rewriting is needed here.
        super().__init__(
            uri or "ws://localhost:8765",
            timeout=timeout,
            connect_timeout=connect_timeout,
        )

    @staticmethod
    def _pin_args(pins: PinCollection):
        if isinstance(pins, (str, int)):
            return (pins,)
        return tuple(pins)

    def on(self, pins: PinCollection):
        return super().on(*self._pin_args(pins))

    def off(self, pins: PinCollection):
        return super().off(*self._pin_args(pins))

    @staticmethod
    def _row_label(row: Union[int, str]) -> str:
        if isinstance(row, int):
            if not 0 <= row <= 15:
                raise ValueError(f"Row out of range: {row}")
            return chr(ord("A") + row)

        label = str(row).strip().upper()
        if len(label) != 1 or not "A" <= label <= "P":
            raise ValueError(f"Invalid row label: {row}")
        return label

    def on_row(self, row: Union[int, str]):
        return super().on("row", self._row_label(row))

    def off_row(self, row: Union[int, str]):
        return super().off("row", self._row_label(row))

    @staticmethod
    def _column_value(col: Union[int, str]) -> str:
        try:
            value = int(str(col).strip())
        except ValueError as exc:
            raise ValueError(f"Invalid column: {col}") from exc

        if not 0 <= value <= 15:
            raise ValueError(f"Column out of range: {value}")
        return str(value)

    def on_col(self, col: Union[int, str]):
        return super().on("col", self._column_value(col))

    def off_col(self, col: Union[int, str]):
        return super().off("col", self._column_value(col))

    def off_all(self):
        return super().alloff()
