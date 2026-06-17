"""Enable `python -m appcategorizer <app name> ...`.

This is the PATH-independent way to run the CLI when the generated
`appcategorizer` console script is not on the system PATH (common on Windows
with Microsoft Store Python or the `py` launcher).
"""

from .cli import main_sync

if __name__ == "__main__":
    main_sync()
