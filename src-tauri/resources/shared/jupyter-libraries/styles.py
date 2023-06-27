from pathlib import Path

from IPython.core.display import HTML


def tufte():
    """Use '../' to work up the tree so that this function works on both
    Windows and macOS.
    """
    stylesheet = Path("../../../config/tufte_inspired.css").read_text()
    return HTML(stylesheet)
