# lgad_ivcv

LGAD IV/CV measurement and switching-matrix control tools.

## IV measurement GUI

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
./run_gui.py
```

The GUI provides individual-channel, row-wise, and column-wise IV measurement,
a 16 by 16 selector, live PAU/SMU plots, per-target and sweep progress, and
safe measurement cancellation. Row-wise and column-wise modes connect all 16
channels in each selected row or column during one sweep. The initial result
directory follows
`IVCV_RESULT_PATH` when it is set, otherwise it is `./result`.

The channel selector is an independent window that opens with the main window.
The independent Live IV window opens automatically when a measurement starts.
Use the `View` menu to reopen either window; the status log remains fixed in the
main window.

Each measurement session writes the timestamped status messages to
`IV_GUI_YYYY-MM-DDTHHMMSS_vN.log` in the same dated session directory as the
IV data and plot files.

The switching matrix URI follows `IVCV_SWITCHING_MATRIX_URI` when it is set,
otherwise it defaults to `ws://localhost:8765`. An explicit `--port` argument
overrides the environment setting in command-line scripts.
