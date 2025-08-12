import os, sys, logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

ROOT = Path(__file__).resolve().parents[1]

DOTENV_FILE = ROOT / ".venv" / "int.venv"

if DOTENV_FILE.exists():
    load_dotenv(DOTENV_FILE, override=False)
else:
    load_dotenv(find_dotenv(usecwd=True), override=False)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTH_KEY = os.getenv("AUTH_KEY")

if not TELEGRAM_TOKEN or not AUTH_KEY:
    print(f"[DEBUG] CWD={os.getcwd()}")
    print(f"[DEBUG] TRIED={DOTENV_FILE} (exists={DOTENV_FILE.exists()})")
    raise SystemExit("Missing TELEGRAM_TOKEN or AUTH_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CERT = os.path.join(os.path.dirname(BASE_DIR), "certs", "russiantrustedca.crt")
VERIFY_CERT_PATH = os.getenv("VERIFY_CERT_PATH", DEFAULT_CERT)
if not os.path.exists(VERIFY_CERT_PATH):
    print(f"⚠️ Certificate not found at {VERIFY_CERT_PATH} (set VERIFY_CERT_PATH or add cert)")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")

LANG_BUTTON = "Язык"
MODE_OPTIONS = {
    "Экшн-тайтлы": "action",
    "Вопросы": "questions",
    "Структура": "structure",
    "Гипотезы": "hypotheses",
    "Фреймворки": "frameworks",
}
LANG_OPTIONS = {"🇷🇺 Русский": "ru", "🇬🇧 Английский": "en"}

BTN_MORE = "Ещё варианты"
BTN_SHORTER = "Короче"
BTN_LONGER = "Длиннее"
BTN_STRAIGHT = "Ближе к исходнику"
BTN_CREATIVE = "Больше креатива"
BTN_PRESS = "Пресс-тест"
BTN_MORE_Q = "Еще вопросы"
BTN_FOLLOWUPS = "Фоллоу-апы"

REFINERS = {
    "action":    [BTN_MORE, BTN_SHORTER, BTN_LONGER, BTN_STRAIGHT, BTN_CREATIVE],
    "questions": [BTN_MORE_Q, BTN_FOLLOWUPS],
    "structure": [BTN_PRESS],
    "hypotheses": [BTN_PRESS],
    "frameworks": [BTN_PRESS],
}