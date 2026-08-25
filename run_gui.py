#!/usr/bin/env python3
"""Launch the LGAD IV measurement GUI from this repository checkout."""

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = REPOSITORY_ROOT.parent

# The package is this repository directory, while swm_ctrl is its sibling.
# Adding their common parent makes both imports work from any current directory.
sys.path.insert(0, str(WORKSPACE_ROOT))

from lgad_ivcv.gui.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
