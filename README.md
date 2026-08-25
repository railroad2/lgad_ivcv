# lgad_ivcv

LGAD IV/CV measurement and switching-matrix control tools.

## IV/CV measurement GUI

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

The bundled `scripts/run_gui.py` launcher adds this directory automatically.

From the repository directory, start the GUI with:

```bash
./scripts/run_gui.py
```

The IV and CV tabs share one result directory setting. The `IVCV_RESULT_PATH`
environment variable takes priority when it is set; otherwise the GUI restores
the shared saved value or uses `./result` initially.

The switching matrix URI is read from `IVCV_SWITCHING_MATRIX_URI` when it is
set; otherwise it defaults to `ws://localhost:8765`. An explicit `--port`
argument overrides the environment setting in command-line scripts.
