import argparse

from lgad_ivcv.ivcv.config import resolve_result_path, resolve_switching_matrix_uri
from lgad_ivcv.ivcv.cv_sw import CV_sw
from lgad_ivcv.scripts.cli_args import channel_number


def measure_selected(
    smport,
    v0,
    v1,
    dv,
    resultpath,
    sensor_name,
    channels,
    rlcr=None,
    rpau=None,
    return_swp=False,
    dryrun=False,
):
    if not channels:
        raise ValueError("at least one channel is required")

    with CV_sw(smport, dryrun) as cvsw:
        cvsw.set_lcr(rlcr)
        cvsw.set_pau(rpau)
        cvsw.ac_level = 0.1
        cvsw.set_basepath(resultpath)
        cvsw.set_sensor_name(sensor_name)
        cvsw.set_sweep(v0, v1, dv, return_swp)
        cvsw.measure_channel(channels)


def main():
    parser = argparse.ArgumentParser(
        description="Measure CV only on explicitly selected switch channels"
    )
    parser.add_argument(
        "channels",
        nargs="+",
        type=channel_number,
        help="Channels as numbers 0..255 or labels A00..P15",
    )
    parser.add_argument("--Vstart", type=float, default=0, help="Start voltage")
    parser.add_argument("--Vend", type=float, default=-10, help="End voltage")
    parser.add_argument("--Vstep", type=float, default=1, help="Voltage step")
    parser.add_argument("--sensorname", default="test", help="Sensor name")
    parser.add_argument(
        "--resultpath",
        default=None,
        help="Result path (default: IVCV_RESULT_PATH or ./result)",
    )
    parser.add_argument("--return_swp", action="store_true", help="Return sweep")
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Dry run with only switching matrix operation",
    )
    parser.add_argument("--lcr", default=None, help="LCR meter resource")
    parser.add_argument("--pau", default=None, help="PAU resource")
    parser.add_argument(
        "-p",
        "--port",
        default=None,
        help="Switching matrix port (default: IVCV_SWITCHING_MATRIX_URI or ws://localhost:8765)",
    )
    args = parser.parse_args()

    measure_selected(
        resolve_switching_matrix_uri(args.port),
        args.Vstart,
        args.Vend,
        args.Vstep,
        resolve_result_path(args.resultpath),
        args.sensorname,
        args.channels,
        args.lcr,
        args.pau,
        args.return_swp,
        args.dryrun,
    )


if __name__ == "__main__":
    main()
