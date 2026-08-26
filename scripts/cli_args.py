import argparse
import re


_MATRIX_LABEL = re.compile(r"^([A-Pa-p])(0[0-9]|1[0-5])$")


def channel_number(value):
    """Parse a channel as either 0..255 or A00..P15."""
    text = str(value).strip()
    match = _MATRIX_LABEL.fullmatch(text)
    if match is not None:
        row = ord(match.group(1).upper()) - ord("A")
        return row * 16 + int(match.group(2))

    try:
        channel = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"channel must be 0..255 or A00..P15: {value}"
        ) from exc

    if not 0 <= channel <= 255:
        raise argparse.ArgumentTypeError(
            f"channel must be 0..255 or A00..P15: {value}"
        )
    return channel
