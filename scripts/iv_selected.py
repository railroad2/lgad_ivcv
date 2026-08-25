import argparse

from lgad_ivcv.ivcv.config import resolve_result_path
from lgad_ivcv.ivcv.iv_sw import IV_sw


def channel_number(value):
    channel = int(value)
    if not 0 <= channel <= 255:
        raise argparse.ArgumentTypeError(
            f"channel must be between 0 and 255: {value}"
        )
    return channel


def measure_selected(
    smport,
    v0,
    v1,
    dv,
    current_compliance,
    resultpath,
    sensor_name,
    channels,
    rsmu=None,
    rpau=None,
    return_swp=False,
    dryrun=False,
):
    if not channels:
        raise ValueError("at least one channel is required")

    with IV_sw(smport, dryrun) as ivsw:
        ivsw.set_smu(rsmu)
        ivsw.set_pau(rpau)
        ivsw.set_basepath(resultpath)
        ivsw.set_sensor_name(sensor_name)
        ivsw.set_sweep(v0, v1, dv, return_swp)
        ivsw.set_compliance(current_compliance)
        ivsw.measure_channel(channels)


def main():
    parser = argparse.ArgumentParser(
        description="Measure IV only on explicitly selected switch channels"
    )
    parser.add_argument(
        "channels",
        nargs="+",
        type=channel_number,
        help="Linear channel numbers (0..255)",
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
    parser.add_argument("--smu", default=None, help="SMU resource")
    parser.add_argument("--pau", default=None, help="PAU resource")
    parser.add_argument(
        "-p",
        "--port",
        default="ws://210.119.41.69:8765",
        help="Switching matrix port",
    )
    parser.add_argument(
        "-I",
        "--Icompliance",
        type=float,
        default=1e-5,
        help="SMU current compliance",
    )
    args = parser.parse_args()

    measure_selected(
        args.port,
        args.Vstart,
        args.Vend,
        args.Vstep,
        args.Icompliance,
        resolve_result_path(args.resultpath),
        args.sensorname,
        args.channels,
        args.smu,
        args.pau,
        args.return_swp,
        args.dryrun,
    )


if __name__ == "__main__":
    main()
