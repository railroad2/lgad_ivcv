from typing import Optional

try:
    from swm_ctrl.websocket_client import WebSocketClientSync
except ModuleNotFoundError as exc:
    if exc.name == "swm_ctrl":
        raise ModuleNotFoundError(
            "GateComm requires the swm_ctrl package. "
            "Install swm_ctrl or add its parent directory to PYTHONPATH."
        ) from exc
    raise

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
