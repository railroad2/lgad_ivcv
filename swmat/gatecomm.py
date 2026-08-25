from collections.abc import Iterable
from typing import Optional, Union

from .protocol import col_pins, row_pins

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

    def on_row(self, row: Union[int, str]):
        return self.on(row_pins(row))

    def off_row(self, row: Union[int, str]):
        return self.off(row_pins(row))

    def on_col(self, col: Union[int, str]):
        return self.on(col_pins(col))

    def off_col(self, col: Union[int, str]):
        return self.off(col_pins(col))

    def off_all(self):
        return super().alloff()
