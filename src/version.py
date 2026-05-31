"""Application identity (1.6.X pre-release line, ShepherdHL experimental fork)."""

APP_SHORT_NAME = "Forza Painter"
APP_DISPLAY_NAME = "Forza Painter 1.6.X (Pre-Release)"
APP_LINE_VERSION = "1.6.X (Pre-Release)"
APP_EXPERIMENTAL_LABEL = "Pre-Release"
BUILD_RELEASE_DATE = "May 30th, 2026"
__version__ = "1.6.X"


def app_title() -> str:
    return APP_DISPLAY_NAME


def app_version_string() -> str:
    return f"{app_title()} · v{__version__}"
