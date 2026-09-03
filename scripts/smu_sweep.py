"""Run a voltage sweep using only a Keithley 2400 SMU."""

import argparse
import datetime
from pathlib import Path

from matplotlib.figure import Figure
import numpy as np

from lgad_ivcv.inst import Keithley2400
from lgad_ivcv.ivcv.config import resolve_result_path


def make_voltage_points(vstart, vend, vstep, return_sweep=False):
    """Return an endpoint-inclusive sweep; ``vstep`` is always a magnitude."""
    if not all(np.isfinite(value) for value in (vstart, vend, vstep)):
        raise ValueError("Sweep voltages must be finite")
    if vstep <= 0:
        raise ValueError("Vstep must be greater than zero")

    if vstart == vend:
        forward = [float(vstart)]
    else:
        direction = 1 if vend > vstart else -1
        step = direction * vstep
        forward = np.arange(vstart, vend, step, dtype=float).tolist()
        if not forward or not np.isclose(forward[-1], vend):
            forward.append(float(vend))

    if return_sweep:
        return np.asarray(forward + forward[::-1], dtype=float)
    return np.asarray(forward, dtype=float)


def _safe_shutdown(smu):
    """Best-effort shutdown that continues if one SMU command fails."""
    actions = (
        ("ramp SMU to 0 V", lambda: smu.set_voltage_ramp(0)),
        ("set SMU directly to 0 V", lambda: smu.set_voltage(0)),
        ("turn SMU output off", lambda: smu.set_output("off")),
    )
    for description, action in actions:
        try:
            action()
        except Exception as exc:
            print(f"WARNING: failed to {description}: {exc}")


def _ramp_to_start(smu, vstart):
    """Move to the first measurement voltage in 1 V steps without taking data."""
    ramp_points = make_voltage_points(0, vstart, 1)[1:]
    if len(ramp_points):
        print(f"Ramping from 0 V to {vstart:g} V")
    for voltage in ramp_points:
        smu.set_voltage(voltage)


def measure_sweep(smu, vstart, vend, vstep, current_compliance,
                  return_sweep=False, terminals="rear"):
    """Configure an open SMU and return requested V, measured V, and I rows."""
    if not np.isfinite(current_compliance) or current_compliance <= 0:
        raise ValueError("Icompliance must be greater than zero")
    if terminals not in ("front", "rear"):
        raise ValueError("terminals must be 'front' or 'rear'")

    voltages = make_voltage_points(vstart, vend, vstep, return_sweep)
    measurements = []

    try:
        smu.initialize()
        smu.set_front_rear(terminals)
        smu.set_current_limit(current_compliance)
        smu.set_voltage(0)
        smu.set_output("on")
        _ramp_to_start(smu, vstart)

        for index, requested_voltage in enumerate(voltages, start=1):
            smu.set_voltage(requested_voltage)
            measured_voltage, measured_current = smu.measure()[:2]
            measurements.append(
                [requested_voltage, measured_voltage, measured_current]
            )
            print(
                f"{index}/{len(voltages)}  "
                f"Vset={requested_voltage:g} V  "
                f"Vmeas={measured_voltage:.6g} V  "
                f"I={measured_current:.6g} A"
            )
    finally:
        _safe_shutdown(smu)

    return np.asarray(measurements, dtype=float)


def linear_fit(data):
    """Fit Ismu = slope * Vsmu + intercept using finite measured values."""
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[1] < 3:
        raise ValueError("Measurement data must contain Vinput, Vsmu, and Ismu")

    vsmu = data[:, 1]
    ismu = data[:, 2]
    valid = np.isfinite(vsmu) & np.isfinite(ismu)
    vsmu = vsmu[valid]
    ismu = ismu[valid]

    if len(vsmu) < 2 or len(np.unique(vsmu)) < 2:
        return None

    slope, intercept = np.polyfit(vsmu, ismu, 1)
    inverse_slope = np.inf if slope == 0 else 1.0 / slope
    return slope, intercept, inverse_slope


def save_plot(data, output_path, sensor_name):
    """Save a Vsmu-Ismu plot and annotate its linear-fit parameters."""
    data = np.asarray(data, dtype=float)
    vsmu = data[:, 1]
    ismu = data[:, 2]
    valid = np.isfinite(vsmu) & np.isfinite(ismu)

    figure = Figure(figsize=(8, 6))
    axis = figure.add_subplot()
    axis.plot(vsmu[valid], ismu[valid], "o-", label="Measured")

    fit = linear_fit(data)
    if fit is None:
        fit_text = "Linear fit unavailable"
    else:
        slope, intercept, inverse_slope = fit
        fit_voltage = np.linspace(vsmu[valid].min(), vsmu[valid].max(), 200)
        fit_current = slope * fit_voltage + intercept
        axis.plot(fit_voltage, fit_current, "--", label="Linear fit")
        fit_text = (
            f"dI/dV = {slope:.6e} A/V\n"
            f"dV/dI = {inverse_slope:.6e} Ohm"
        )

    axis.text(
        0.03,
        0.97,
        fit_text,
        transform=axis.transAxes,
        ha="left",
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )
    axis.set_title(f"{sensor_name} - Keithley 2400 IV Sweep")
    axis.set_xlabel("Vsmu (V)")
    axis.set_ylabel("Ismu (A)")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="lower right")
    figure.tight_layout()

    plot_path = Path(output_path).with_suffix(".png")
    figure.savefig(plot_path, dpi=150)
    return plot_path


def save_results(data, resultpath, sensor_name):
    """Save text results and their IV plot below the standard result directory."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    safe_sensor_name = sensor_name.replace("/", "_").replace("\\", "_")
    output_dir = Path(resultpath) / timestamp[:10] / safe_sensor_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"IV_{safe_sensor_name}_smu_{timestamp}.txt"
    version = 1
    while output_path.exists():
        output_path = output_dir / (
            f"IV_{safe_sensor_name}_smu_{timestamp}_v{version}.txt"
        )
        version += 1

    np.savetxt(
        output_path,
        data,
        header="Vinput(V)\tVsmu(V)\tIsmu(A)",
        delimiter="\t",
    )
    save_plot(data, output_path, sensor_name)
    return output_path


def run_sweep(vstart, vend, vstep, current_compliance, resultpath,
              sensor_name, resource=None, return_sweep=False,
              terminals="rear"):
    """Open the Keithley 2400, run one sweep, save it, and close the VISA link."""
    smu = Keithley2400()
    if resource is None:
        print("Looking for the SMU")
        resource = smu.find_inst()
    if resource is None:
        raise RuntimeError("Keithley 2400 SMU was not found")

    smu.open(resource)
    print(f"SMU is connected: {resource}")
    try:
        data = measure_sweep(
            smu,
            vstart,
            vend,
            vstep,
            current_compliance,
            return_sweep,
            terminals,
        )
    finally:
        smu.close()

    output_path = save_results(data, resultpath, sensor_name)
    print(f"Results saved: {output_path}")
    print(f"Plot saved: {output_path.with_suffix('.png')}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Run one voltage sweep using only a Keithley 2400 SMU"
    )
    parser.add_argument("--Vstart", type=float, default=0, help="Start voltage")
    parser.add_argument("--Vend", type=float, default=-10, help="End voltage")
    parser.add_argument(
        "--Vstep", type=float, default=1, help="Positive voltage-step magnitude"
    )
    parser.add_argument("--sensorname", default="test", help="Sensor name")
    parser.add_argument(
        "--resultpath",
        default=None,
        help="Result path (default: IVCV_RESULT_PATH or ./result)",
    )
    parser.add_argument(
        "--return_swp", action="store_true", help="Add a return sweep"
    )
    parser.add_argument(
        "--smu", default=None, help="Keithley 2400 VISA resource"
    )
    parser.add_argument(
        "--terminals",
        choices=("front", "rear"),
        default="rear",
        help="SMU terminals to use",
    )
    parser.add_argument(
        "-I",
        "--Icompliance",
        type=float,
        default=1e-5,
        help="SMU current compliance",
    )
    args = parser.parse_args()

    run_sweep(
        args.Vstart,
        args.Vend,
        args.Vstep,
        args.Icompliance,
        resolve_result_path(args.resultpath),
        args.sensorname,
        args.smu,
        args.return_swp,
        args.terminals,
    )


if __name__ == "__main__":
    main()
