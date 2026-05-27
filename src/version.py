"""Application identity (experimental 1.6.x line, separate from upstream forza-painter FH6 branding)."""

APP_DISPLAY_NAME = "Forza Painter 1.6.X"
APP_EXPERIMENTAL_LABEL = "Experimental"
__version__ = "1.6.6"


def app_title() -> str:
    return f"{APP_DISPLAY_NAME} ({APP_EXPERIMENTAL_LABEL})"


def app_version_string() -> str:
    return f"{app_title()} · v{__version__}"
