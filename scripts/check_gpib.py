"""Query ``*IDN?`` at one explicitly supplied GPIB address."""

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lgad_ivcv.inst.backend import parse_gpib_resource, query_identity


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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query *IDN? at one NI GPIB-USB-HS address"
    )
    parser.add_argument(
        "address",
        type=gpib_resource,
        help="primary address (for example 24 or GPIB0::24::INSTR)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        identity = query_identity(args.address)
        if not identity:
            raise RuntimeError("empty *IDN? response")
    except Exception as exc:
        print(f"ERROR: {args.address}: {exc}", file=sys.stderr)
        return 1

    print(f"{args.address}: {identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
