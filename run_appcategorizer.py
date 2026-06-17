"""Root-level convenience launcher for the appcategorizer CLI.

Running `python run_appcategorizer.py <app name> ...` is equivalent to the
installed `appcategorizer` console script. The real argument parsing, progress
display, and mode handling all live in `appcategorizer.cli`, so this file is a
thin forwarder with no duplicated logic.
"""

from appcategorizer.cli import main_sync

if __name__ == "__main__":
    main_sync()
