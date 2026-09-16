import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# AUDIO
# ============================================================

INPUT_DEVICE = int(
    os.getenv("INPUT_DEVICE", "2")
)

OUTPUT_DEVICE = int(
    os.getenv("OUTPUT_DEVICE", "1")
)

MIC_RATE = 48000
WAKE_RATE = 16000
OPENAI_RATE = 24000
SPEAKER_RATE = 48000

CHANNELS = 1


# ============================================================
# VOLUME
# ============================================================

DEFAULT_VOLUME = int(
    os.getenv(
        "DEFAULT_VOLUME",
        "50",
    )
)

DEFAULT_VOLUME_STEP = int(
    os.getenv(
        "DEFAULT_VOLUME_STEP",
        "10",
    )
)

STATE_DIR = (
    BASE_DIR
    / "state"
)

VOLUME_STATE_FILE = (
    STATE_DIR
    / "volume.json"
)


# ============================================================
# OPENAI
# ============================================================

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-realtime-2.1-mini",
)

WEB_MODEL = os.getenv(
    "WEB_MODEL",
    "gpt-5.6-luna",
)

LINK_SELECTOR_MODEL = os.getenv(
    "LINK_SELECTOR_MODEL",
    "gpt-5.6-luna",
)

VOICE = os.getenv(
    "VOICE",
    "marin",
)


# ============================================================
# WAKE WORD
# ============================================================

WAKE_THRESHOLD = float(
    os.getenv(
        "WAKE_THRESHOLD",
        "0.20",
    )
)

WAKE_CHUNK_16K = 1280

MODELS_DIR = (
    BASE_DIR
    / "wakeword"
    / "models"
)

MELSPEC_MODEL = (
    MODELS_DIR
    / "melspectrogram.onnx"
)

EMBEDDING_MODEL = (
    MODELS_DIR
    / "embedding_model.onnx"
)

WAKE_MODEL = (
    MODELS_DIR
    / "hey_jarvis_v0.1.onnx"
)


# ============================================================
# CONVERSATION
# ============================================================

CONVERSATION_TIMEOUT = int(
    os.getenv(
        "CONVERSATION_TIMEOUT",
        "20",
    )
)


# ============================================================
# WEB / BROWSER
# ============================================================

CHROMIUM_PATH = os.getenv(
    "CHROMIUM_PATH",
    "/usr/bin/chromium",
)

MAX_PAGE_CHARS = 30000

MAX_SITE_PAGE_CHARS = 12000

MAX_SITE_RESULT_CHARS = 45000

MAX_SITE_PAGES = int(
    os.getenv(
        "MAX_SITE_PAGES",
        "5",
    )
)

MAX_SITE_DEPTH = int(
    os.getenv(
        "MAX_SITE_DEPTH",
        "2",
    )
)

MAX_LINKS_FOR_SELECTION = int(
    os.getenv(
        "MAX_LINKS_FOR_SELECTION",
        "40",
    )
)

SITE_LINKS_PER_STEP = int(
    os.getenv(
        "SITE_LINKS_PER_STEP",
        "3",
    )
)

MAX_LINK_SELECTION_CALLS = int(
    os.getenv(
        "MAX_LINK_SELECTION_CALLS",
        "3",
    )
)


# ============================================================
# PROMPTS
# ============================================================

PROMPT_FILE = (
    BASE_DIR
    / "prompts"
    / "scarlett.txt"
)
