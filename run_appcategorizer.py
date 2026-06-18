# Copyright (c) 2026, Sorbonne Université, CNRS, LIP6.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the
# GNU Lesser General Public License v3.0 (LGPL-3.0-only)
# which accompanies this distribution, and is available at
# https://www.gnu.org/licenses/lgpl-3.0.en.html

"""Root-level convenience launcher for the appcategorizer CLI.

Running `python run_appcategorizer.py <app name> ...` is equivalent to the
installed `appcategorizer` console script. The real argument parsing, progress
display, and mode handling all live in `appcategorizer.cli`, so this file is a
thin forwarder with no duplicated logic.
"""

from appcategorizer.cli import main_sync

if __name__ == "__main__":
    main_sync()
