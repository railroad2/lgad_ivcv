from serial.tools import list_ports

from swm_ctrl.websocket_client import parse_pin_tokens

try:
    from .print_utils import print_with_frame
    from .usbcomm import USBComm
except ImportError:
    from print_utils import print_with_frame
    from usbcomm import USBComm
    

def find_pico_ports():
    """Return a list of candidate serial device names for Pico/MicroPython."""
    candidates = []
    for i in list_ports.comports():
        m = (i.manufacturer or "").lower()
        d = (i.description or "").lower()
        vid = i.vid or 0
        pid = i.pid or 0
        # Heuristics: match on manufacturer/description or known VID/PID
        if (
            "micropython" in m
            or "raspberry" in m
            or "pico" in d
            or "rp2" in d
            or (vid, pid) in {(0x2E8A, 0x0005), (0x2E8A, 0x000A)}  # examples
            ):
            candidates.append(i.device)

    return candidates

def send_line(line, port=None):
    return _send_json_command(line, port=port)


def _row_pins(row):
    if isinstance(row, int):
        if not 0 <= row <= 15:
            raise ValueError(f"Row out of range: {row}")
        row = chr(ord("A") + row)

    return parse_pin_tokens(("row", str(row).strip().upper()))


def _col_pins(col):
    return parse_pin_tokens(("col", str(col).strip()))


def _send_json_command(cmd, port=None):
    if port is None:
        ports = find_pico_ports()
        if not ports:
            raise RuntimeError("No Raspberry Pi Pico serial port found")
        port = ports[0]

    return USBComm(port=port).send_data_once(cmd)


def sw_onoff(ch, onoff, port=None):
    if isinstance(ch, str) and ch.strip().lower() == "all":
        if onoff:
            raise ValueError("Turning all pins on is not supported")
        cmd = {"cmd": "ALLOFF"}
    else:
        tokens = (ch,) if isinstance(ch, (str, int)) else tuple(ch)
        pins = parse_pin_tokens(tokens)
        cmd = {"cmd": "ON" if onoff else "OFF", "pins": pins}

    return _send_json_command(cmd, port=port)


def on_row(row, port=None):
    return sw_onoff(_row_pins(row), True, port=port)


def off_row(row, port=None):
    return sw_onoff(_row_pins(row), False, port=port)


def on_col(col, port=None):
    return sw_onoff(_col_pins(col), True, port=port)


def off_col(col, port=None):
    return sw_onoff(_col_pins(col), False, port=port)


def pinstat(ch=None, frame=True, color=True, port=None):
    cmd = {"cmd":"PINSTAT", "which":"ALL"}
    res = _send_json_command(cmd, port=port)
    pins = [int(i) for i in res["pins"]]
    print_with_frame(pins, ch, frame, color)

    return pins
