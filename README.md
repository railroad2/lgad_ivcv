# lgad_ivcv

LGAD IV/CV measurement and switching-matrix control tools.

## Setup

Install the dependencies from the repository directory:

```bash
python3 -m pip install -r requirements.txt
```

The `swm_ctrl` package must be importable for WebSocket switching-matrix
control. If `lgad_ivcv` and `swm_ctrl` are sibling repositories, add their
common parent directory to `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/parent/directory:${PYTHONPATH}
```

The switching matrix URI is read from `IVCV_SWITCHING_MATRIX_URI` when it is
set; otherwise it defaults to `ws://localhost:8765`. An explicit `--port`
argument overrides the environment setting in command-line scripts.

Measurement results are written below `IVCV_RESULT_PATH` when it is set and
below `./result` otherwise. An explicit `--resultpath` argument overrides this
setting in command-line scripts.

## GUI measurement

The bundled launcher adds the common repository parent to `PYTHONPATH`
automatically. From the repository directory, start the GUI with:

```bash
./scripts/run_gui.py
```

## Command-line measurement

Run a script with `--help` to see every instrument and sweep option:

```bash
python3 scripts/iv_all.py --help
python3 scripts/cv_all.py --help
```

`iv_all.py` and `cv_all.py` measure all 256 switching-matrix channels when no
channel numbers are supplied. Supplying channel numbers limits the measurement
to those channels:

```bash
# Measure IV on every channel.
python3 scripts/iv_all.py --sensorname sensor01

# Measure IV on channels 0, 17, and 255.
python3 scripts/iv_all.py 0 17 255 \
    --sensorname sensor01 --Vstart 0 --Vend -10 --Vstep 1

# Measure CV on every channel.
python3 scripts/cv_all.py --sensorname sensor01

# Measure CV on channels 0, 17, and 255.
python3 scripts/cv_all.py 0 17 255 \
    --sensorname sensor01 --Vstart 0 --Vend -10 --Vstep 1
```

The selected-channel scripts require at least one channel. They accept either
linear channel numbers `0..255` or matrix labels `A00..P15`:

```bash
python3 scripts/iv_selected.py A00 C02 P15 --sensorname sensor01
python3 scripts/cv_selected.py A00 C02 P15 --sensorname sensor01
```

For IV measurements, complete rows or columns can be connected during each
sweep. Rows accept either numbers `0..15` or labels `A..P`; columns use numbers
`0..15`. Omitting the row or column arguments measures all 16 groups:

```bash
python3 scripts/iv_row.py A B C --sensorname sensor01
python3 scripts/iv_col.py 0 1 2 --sensorname sensor01
```

Use the `once` scripts to run one sweep without selecting a switching-matrix
channel:

```bash
python3 scripts/iv_once.py --sensorname sensor01
python3 scripts/cv_once.py --sensorname sensor01
```

To sweep and measure with only the Keithley 2400 SMU (without the switching
matrix or picoammeter), use `smu_sweep.py`:

```bash
python3 scripts/smu_sweep.py \
    --sensorname sensor01 --Vstart 0 --Vend -100 --Vstep 1 \
    --Icompliance 1e-5 --smu 'ASRL/dev/ttyUSB0::INSTR'
```

When `--smu` is omitted, the script searches for the Keithley 2400. Results
contain the requested voltage, measured SMU voltage, and measured SMU current.
Before measurement, the SMU ramps from 0 V to `--Vstart` in fixed 1 V
increments, independently of `--Vstep`.

### Measuring instruments

The measurement programs use PyVISA resource names to open the instruments:

| Measurement | Option | Instrument | VISA resource name |
| --- | --- | --- | --- |
| IV | `--smu` | Keithley 2400 SMU | Searched automatically when omitted |
| IV | `--pau` | Keithley 6487 picoammeter | Searched automatically when omitted |
| CV | `--lcr` | Wayne Kerr 4300 LCR meter | Searched automatically when omitted |
| CV | `--pau` | (Optional) Keithley 6487 picoammeter/bias source | Not searched automatically |

List the VISA resources visible to Python with:

```bash
python3 - <<'PY'
import pyvisa

print(*pyvisa.ResourceManager().list_resources(), sep="\n")
PY
```

Pass the exact resource names from this list when automatic detection is not
appropriate. For example:

```bash
python3 scripts/iv_selected.py 0 17 255 \
    --sensorname sensor01 \
    --smu 'ASRL/dev/ttyUSB0::INSTR' \
    --pau 'ASRL/dev/ttyUSB1::INSTR'

python3 scripts/cv_selected.py 0 17 255 \
    --sensorname sensor01 \
    --lcr 'ASRL/dev/ttyUSB2::INSTR' \
    --pau 'ASRL/dev/ttyUSB1::INSTR'
```

Automatic detection examines VISA resources whose names contain `ttyUSB`,
queries each device with `*IDN?`, and selects the resource whose identification
matches the expected instrument model. Resources using another transport or
device name must be supplied explicitly.

IV measurement requires the SMU for voltage bias and can also use the
picoammeter for an additional current reading. CV measurement requires the LCR
meter. The PAU is optional for CV. When `--pau` is omitted, the LCR meter
supplies the DC bias and the negative bias is limited to -40 V. Supplying a
Keithley 6487 resource with `--pau` selects it as the external bias source.

### Dry run

Use `--dryrun` with a switching-matrix script to verify the selected channels,
rows, or columns without operating the IV/CV measurement instruments:

```bash
python3 scripts/iv_all.py 0 17 255 --dryrun --sensorname sensor01
python3 scripts/iv_row.py A B C --dryrun --sensorname sensor01
python3 scripts/cv_selected.py A00 C02 P15 --dryrun --sensorname sensor01
```

Dry-run mode still connects to the switching-matrix gateway and physically
turns the requested switches on and off. It therefore requires a working
switching matrix and must not be treated as a hardware-free simulation. The
SMU, LCR meter, and PAU are not opened, and no IV/CV measurement data are
produced.

CLI dry-run scripts do not publish measurement progress to the web monitor.
The `iv_once.py` and `cv_once.py` scripts do not support `--dryrun` because they
run without switching-matrix channel selection.

## Acknowledgements

Development of this project was assisted by OpenAI Codex.
