"""Application identity (1.6.X beta line, ShepherdHL experimental fork)."""

APP_SHORT_NAME = "Forza Painter"
APP_DISPLAY_NAME = "Forza Painter 1.6.X Beta-2"
APP_LINE_VERSION = "v.1.6.X Beta-2"
APP_EXPERIMENTAL_LABEL = "Beta-2"
BUILD_RELEASE_DATE = "6/3/2026 at 11:00AM"
__version__ = "1.6.X-beta-2"

GENERATOR_AUTHOR = 'ShepherdHL, "Walker"'
REPOSITORY_URL = "https://github.com/ShepherdHL/forza-painter-fh6"


def app_title() -> str:
    return APP_DISPLAY_NAME


def app_version_string() -> str:
    return f"{app_title()} · {APP_LINE_VERSION}"
