from __future__ import annotations

from app_paths import ROOT, SOURCE_DIR


# Paths
APP_DIR = SOURCE_DIR
PROBE_DIR = ROOT / "webui-data" / "probes"
SESSION_PATH = PROBE_DIR / "current-fh6-session.json"
TYPECODE_IMPORT_DIR = ROOT / "runtime" / "typecode-import"
TYPECODE_EXPORT_DIR = ROOT / "runtime" / "typecode-export"
MEMORY_WORK_CONSENT_FLAG = ROOT / "runtime" / "settings" / "memory_work_consent.flag"


# Limits / thresholds
MEMORY_SNAPSHOT_LIMIT_MB = 2048
PREVIEW_MAX = 520
PREVIEW_MAIN_MIN = 360
PREVIEW_FILTER_CARD_MIN = 160
PREVIEW_FILTER_THUMB_W = 240
PREVIEW_FILTER_THUMB_H = 140
GENERATE_COMPARE_SOURCE_MIN = 200
GENERATE_COMPARE_RESULT_MIN = 260
DETAILED_LOG_OUTPUT_LIMIT = 50000
DETAILED_LOG_MEMORY_LIMIT = 120000
FH6_AUTO_LOCATE_MAX_SECONDS = 300
FH6_AUTO_LOCATE_TIMEOUT_SECONDS = 360
UPDATE_CHECK_TIMEOUT_SECONDS = 8

# Experimental eco / cool-GPU generation (between-image cooldown)
ECO_GPU_COOLDOWN_TARGET_C = 75.0
ECO_GPU_COOLDOWN_MAX_WAIT_SECONDS = 300.0
ECO_GPU_COOLDOWN_POLL_SECONDS = 2.0
ECO_GPU_FIXED_PAUSE_SECONDS = 30.0


# Update URLs
UPDATE_CHANGELOG_URL = "https://raw.githubusercontent.com/ShepherdHL/forza-painter-fh6/main/CHANGELOG.md"
UPDATE_RELEASE_URL = "https://github.com/ShepherdHL/forza-painter-fh6/releases/latest"

