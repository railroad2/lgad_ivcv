import argparse

from lgad_ivcv.ivcv.config import resolve_result_path
from lgad_ivcv.ivcv.cv_sw import CV_sw


def measure_once(
    v0,
    v1,
    dv,
    resultpath,
    sensor_name,
    rlcr=None,
    rpau=None,
    return_swp=False,
):
    # port=None leaves SWmat unopened; this run does not select any channel.
    with CV_sw(port=None, dryrun=False) as cvsw:
        cvsw.set_lcr(rlcr)
        cvsw.set_pau(rpau)
        cvsw.ac_level = 0.1
        cvsw.set_basepath(resultpath)
        cvsw.set_sensor_name(sensor_name)
        cvsw.set_sweep(v0, v1, dv, return_swp)
        cvsw.measure(0, 0, target_label="single")


def main():
    parser = argparse.ArgumentParser(
        description="Run one CV sweep without switching-matrix channel selection"
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
    parser.add_argument("--lcr", default=None, help="LCR meter resource")
    parser.add_argument("--pau", default=None, help="PAU resource")
    args = parser.parse_args()

    measure_once(
        args.Vstart,
        args.Vend,
        args.Vstep,
        resolve_result_path(args.resultpath),
        args.sensorname,
        args.lcr,
        args.pau,
        args.return_swp,
    )


if __name__ == "__main__":
    main()
