# lgad_ivcv

LGAD IV/CV measurement and switching-matrix control tools.

## IV/CV measurement GUI

Install the dependencies from the repository directory:

```bash
python3 -m pip install -r requirements.txt
```

From the directory containing this repository, start the GUI with:

```bash
python3 -m lgad_ivcv.gui
```

Alternatively, run the launcher directly from the repository:

```bash
./scripts/run_gui.py
```

The `IV` tab provides individual-channel, row-wise, and column-wise
measurements, live PAU/SMU plots, per-target and sweep progress, and safe
measurement cancellation. Row-wise and column-wise modes connect all 16
channels in each selected row or column during one sweep.

The `CV` tab measures individual channels, complete rows, or complete columns
with an LCR meter. It supports configurable bias sweep, AC level, and
frequency, plus an optional PAU for external bias. Without a PAU, the GUI
rejects bias settings below the LCR meter's -40 V limit. Live capacitance and
resistance plots open when a CV measurement starts.

The IV and CV tabs share one result directory setting. `IVCV_RESULT_PATH` takes
priority when it is set; otherwise the GUI restores the shared saved value or
uses `./result` initially.

The channel selector is an independent window that opens with the main window.
The independent Live IV or Live CV window opens automatically when its
measurement starts. Use the `View` menu to reopen the channel selector and live
plot windows; the status logs remain fixed in their respective main-window
tabs.

Each measurement session writes timestamped status messages to
`IV_GUI_YYYY-MM-DDTHHMMSS_vN.log` or `CV_GUI_YYYY-MM-DDTHHMMSS_vN.log` in the
same dated session directory as its data and plot files. If a finished,
stopped, or failed session contains only log files, the GUI appends `_logonly`
to that session directory name.

Session directory names identify the measurement mode: `IV_PIXEL_...`,
`IV_ROW_...`, and `IV_COL_...` for IV measurements, and `CV_PIXEL_...`,
`CV_ROW_...`, and `CV_COL_...` for CV measurements.

The switching matrix URI follows `IVCV_SWITCHING_MATRIX_URI` when it is set,
otherwise it defaults to `ws://localhost:8765`. An explicit `--port` argument
overrides the environment setting in command-line scripts.
