"""Query ``*IDN?`` at one explicitly supplied GPIB address."""

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lgad_ivcv.inst.backend import (
    InstrumentBackend,
    parse_gpib_resource,
    query_identity,
)


def gpib_resource(value):
    """Normalize an address number or VISA-style GPIB resource name."""
    text = str(value).strip()
    if text.isdecimal():
        text = f"GPIB0::{int(text)}::INSTR"

    try:
        parsed = parse_gpib_resource(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if parsed is None:
        raise argparse.ArgumentTypeError(
            "address must be a number or GPIB0::<address>::INSTR"
        )

    board, address = parsed
    return f"GPIB{board}::{address}::INSTR"


def positive_timeout(value):
    """Parse a positive timeout in seconds for argparse."""
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than zero")
    return timeout


def query_gpib_identity(resource_name, timeout):
    """Query one GPIB address using a short controller transfer timeout."""
    backend = InstrumentBackend(gpib_timeout_seconds=timeout)
    try:
        return query_identity(resource_name, backend=backend)
    finally:
        backend.close()


def check_gpib_adapter(timeout):
    """Initialize the USB adapter without addressing an instrument."""
    backend = InstrumentBackend(gpib_timeout_seconds=timeout)
    try:
        return backend.initialize_gpib_adapter()
    finally:
        backend.close()


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Initialize NI GPIB-USB-HS or query *IDN? at one GPIB address"
        )
    )
    parser.add_argument(
        "address",
        nargs="?",
        type=gpib_resource,
        help="optional primary address (for example 24 or GPIB0::24::INSTR)",
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout,
        default=1.0,
        help="GPIB response timeout in seconds (default: 1.0)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.address is None:
        try:
            serial = check_gpib_adapter(args.timeout) or "unknown"
        except Exception as exc:
            print(f"ERROR: NI GPIB-USB-HS: {exc}", file=sys.stderr)
            return 1

        print("NI GPIB-USB-HS: INITIALIZED")
        print(f"Serial: {serial}")
        print("Instrument connection: NOT CHECKED")
        return 0

    try:
        identity = query_gpib_identity(args.address, args.timeout)
        if not identity:
            raise RuntimeError("empty *IDN? response")
    except Exception as exc:
        print(f"ERROR: {args.address}: {exc}", file=sys.stderr)
        return 1

    print(f"{args.address}: {identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
