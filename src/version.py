"""Application identity (1.6.X beta line, ShepherdHL experimental fork)."""

APP_SHORT_NAME = "Forza Painter"
APP_DISPLAY_NAME = "Forza Painter 1.6.X (Beta)"
APP_LINE_VERSION = "1.6.X (Beta)"
APP_EXPERIMENTAL_LABEL = "Beta"
BUILD_RELEASE_DATE = "May 30th, 2026"
__version__ = "1.6.X"

GENERATOR_AUTHOR = 'ShepherdHL, "Walker"'
REPOSITORY_URL = "https://github.com/ShepherdHL/forza-painter-fh6"


def app_title() -> str:
    return APP_DISPLAY_NAME


def app_version_string() -> str:
    return f"{app_title()} · v{__version__}"
