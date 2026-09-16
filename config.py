import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# AUDIO
# ============================================================

def _audio_device(
    env_name,
    default,
):

    # Index PortAudio (entier) ou nom
    # de périphérique ALSA (chaîne),
    # ex. "scarlett_out" défini dans
    # /etc/asound.conf.

    raw = os.getenv(
        env_name,
        default,
    )

    try:

        return int(raw)

    except ValueError:

        return raw


INPUT_DEVICE = _audio_device(
    "INPUT_DEVICE",
    "2",
)

OUTPUT_DEVICE = _audio_device(
    "OUTPUT_DEVICE",
    "1",
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
# SPOTIFY
# ============================================================

SPOTIFY_CLIENT_ID = os.getenv(
    "SPOTIFY_CLIENT_ID",
    "",
)

SPOTIFY_CLIENT_SECRET = os.getenv(
    "SPOTIFY_CLIENT_SECRET",
    "",
)

SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:8888/callback",
)

SPOTIFY_DEVICE_NAME = os.getenv(
    "SPOTIFY_DEVICE_NAME",
    "Scarlett",
)

SPOTIFY_CACHE_FILE = (
    STATE_DIR
    / "spotify_token.json"
)

SPOTIFY_SCOPES = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-read-collaborative"
)


# ============================================================
# PROMPTS
# ============================================================

PROMPT_FILE = (
    BASE_DIR
    / "prompts"
    / "scarlett.txt"
)
