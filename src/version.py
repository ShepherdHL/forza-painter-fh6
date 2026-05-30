"""Application identity (experimental 1.6.x line, separate from upstream forza-painter FH6 branding)."""

APP_SHORT_NAME = "Forza Painter"
APP_DISPLAY_NAME = "Forza Painter 1.6.X"
APP_LINE_VERSION = "1.6.X"
APP_EXPERIMENTAL_LABEL = "Experimental™"
BUILD_RELEASE_DATE = "May 28th, 2026"
__version__ = "1.6.6"


def app_title() -> str:
    return APP_DISPLAY_NAME


def app_version_string() -> str:
    return f"{app_title()} · v{__version__}"
