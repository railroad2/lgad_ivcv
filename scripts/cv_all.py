import argparse

from lgad_ivcv.ivcv.cv_sw import CV_sw

def measure_all(smport, v0, v1, dv,
                basepath, sensor_name,
                rlcr=None, rpau=None,
                channels=None, return_swp=False, dryrun=False):
    if channels is None:
        channels = []

    with CV_sw(smport, dryrun) as cvsw:
        cvsw.set_lcr(rlcr)
        cvsw.set_pau(rpau)
        cvsw.ac_level = 0.1
        cvsw.set_basepath(basepath)
        cvsw.set_sensor_name(sensor_name)
        cvsw.set_sweep(v0, v1, dv, return_swp)

        if channels:
            cvsw.measure_channel(channels)
        else:
            cvsw.measure_all_channels()


def main():
    parser = argparse.ArgumentParser(description="Measure CV by switch channel")
    parser.add_argument('items', nargs="*", type=int, help="Linear channel numbers (0..255)")
    parser.add_argument('--Vstart', type=float, default=0, help="Start voltage")
    parser.add_argument('--Vend', type=float, default=-10, help="End voltage")
    parser.add_argument('--Vstep', type=float, default=1, help="Voltage step")
    parser.add_argument('--sensorname', default='test', help="Sensor name")
    parser.add_argument('--basepath', default='./result', help="Base path for result output")
    parser.add_argument('--return_swp', action="store_true", help="Return sweep")
    parser.add_argument('--dryrun', action="store_true", help="Dry run with only switching matrix operation")
    parser.add_argument('--lcr', default=None, help="LCR meter resource")
    parser.add_argument('--pau', default=None, help="PAU resource")
    parser.add_argument('-p', '--port', default='ws://210.119.41.69:8765', help="Switching matrix port")

    args = parser.parse_args()

    measure_all(
        args.port, args.Vstart, args.Vend, args.Vstep,
        args.basepath, args.sensorname,
        args.lcr, args.pau,
        args.items, args.return_swp, args.dryrun,
    )


if __name__=="__main__":
    main()
