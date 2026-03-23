import argparse
from lgad_ivcv.ivcv import iv_sw


def measure_rows(smport, v0, v1, dv, Icomp,
                 basepath, sensor_name,
                 rows=None, rsmu=None, rpau=None,
                 return_swp=False, dryrun=False):
    ivsw = iv_sw.IV_sw(smport, dryrun)

    ivsw.set_smu(rsmu)
    ivsw.set_pau(rpau)
    ivsw.set_basepath(basepath)
    ivsw.set_sensor_name(sensor_name)
    ivsw.set_sweep(v0, v1, dv, return_swp)
    ivsw.set_compliance(Icomp)
    ivsw.measure_rows(rows)


def main():
    parser = argparse.ArgumentParser(description="Measure IV with all 16 pixels in each row connected together.")
    parser.add_argument("items", nargs="*", default=[], help="Row numbers")
    parser.add_argument("--Vstart", required=False, default=0, help="Start voltage")
    parser.add_argument("--Vend", required=False, default=-10, help="End voltage")
    parser.add_argument("--Vstep", required=False, default=1, help="Voltage step")
    parser.add_argument("--sensorname", required=False, default="test", help="Sensor name")
    parser.add_argument("--basepath", required=False, default=None, help="Base path for result output")
    parser.add_argument("--return_swp", required=False, action="store_true", help="Return sweep")
    parser.add_argument("--dryrun", required=False, action="store_true", help="Dry run with only switching matrix operation")
    parser.add_argument("--smu", required=False, default=None, help="SMU resource")
    parser.add_argument("--pau", required=False, default=None, help="PAU resource")
    parser.add_argument("-p", "--port", required=False, default="ws://localhost:3001", help="Switching matrix port")
    parser.add_argument("-I", "--Icompliance", required=False, default=1e-5, help="SMU current compliance")

    args = parser.parse_args()

    rows = [int(i) for i in args.items]
    port = args.port

    v0 = float(args.Vstart)
    v1 = float(args.Vend)
    dv = float(args.Vstep)

    Icomp = float(args.Icompliance)

    sensor_name = args.sensorname
    return_swp = args.return_swp
    dryrun = args.dryrun
    rsmu = args.smu
    rpau = args.pau

    if args.basepath is None:
        basepath = "../../result/"
    else:
        basepath = args.basepath

    measure_rows(port, v0, v1, dv, Icomp,
                 basepath, sensor_name,
                 rows, rsmu, rpau,
                 return_swp, dryrun)


if __name__ == "__main__":
    main()
