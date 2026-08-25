import argparse

from lgad_ivcv.ivcv.iv_sw import IV_sw
from lgad_ivcv.ivcv.config import resolve_result_path, resolve_switching_matrix_uri


def measure_rows(smport, v0, v1, dv, Icomp,
                 resultpath, sensor_name,
                 rows=None, rsmu=None, rpau=None,
                 return_swp=False, dryrun=False):
    with IV_sw(smport, dryrun) as ivsw:
        ivsw.set_smu(rsmu)
        ivsw.set_pau(rpau)
        ivsw.set_basepath(resultpath)
        ivsw.set_sensor_name(sensor_name)
        ivsw.set_sweep(v0, v1, dv, return_swp)
        ivsw.set_compliance(Icomp)
        ivsw.measure_rows(rows)


def main():
    parser = argparse.ArgumentParser(description="Measure IV with all 16 pixels in each row connected together.")
    parser.add_argument("items", nargs="*", type=int, help="Row numbers (0..15)")
    parser.add_argument("--Vstart", type=float, default=0, help="Start voltage")
    parser.add_argument("--Vend", type=float, default=-10, help="End voltage")
    parser.add_argument("--Vstep", type=float, default=1, help="Voltage step")
    parser.add_argument("--sensorname", default="test", help="Sensor name")
    parser.add_argument("--resultpath", default=None, help="Result path (default: IVCV_RESULT_PATH or ./result)")
    parser.add_argument("--return_swp", action="store_true", help="Return sweep")
    parser.add_argument("--dryrun", action="store_true", help="Dry run with only switching matrix operation")
    parser.add_argument("--smu", default=None, help="SMU resource")
    parser.add_argument("--pau", default=None, help="PAU resource")
    parser.add_argument(
        "-p", "--port", default=None,
        help="Switching matrix port (default: IVCV_SWITCHING_MATRIX_URI or ws://localhost:8765)",
    )
    parser.add_argument("-I", "--Icompliance", type=float, default=1e-5, help="SMU current compliance")

    args = parser.parse_args()

    measure_rows(
        resolve_switching_matrix_uri(args.port),
        args.Vstart, args.Vend, args.Vstep, args.Icompliance,
        resolve_result_path(args.resultpath), args.sensorname,
        args.items, args.smu, args.pau,
        args.return_swp, args.dryrun,
    )


if __name__ == "__main__":
    main()
