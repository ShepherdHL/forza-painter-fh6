"""Application identity (1.6.X beta line, ShepherdHL experimental fork)."""

APP_SHORT_NAME = "Forza Painter"
APP_DISPLAY_NAME = "Forza Painter 1.6.X Beta-3"
APP_LINE_VERSION = "v.1.6.X Beta-3"
APP_EXPERIMENTAL_LABEL = "Beta-3"
BUILD_RELEASE_DATE = "6/3/2026 at 7:42PM"
__version__ = "1.6.X-beta-3"

GENERATOR_AUTHOR = 'ShepherdHL, "Walker"'
REPOSITORY_URL = "https://github.com/ShepherdHL/forza-painter-fh6"


def app_title() -> str:
    return APP_DISPLAY_NAME


def app_version_string() -> str:
    return f"{app_title()} · {APP_LINE_VERSION}"
