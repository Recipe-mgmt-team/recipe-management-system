"""Settings read from environment variables or a local .env file."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv(path: str) -> None:
    """Tiny .env reader so the project has no extra dependency for it."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "recipes.db"))

# USDA FoodData Central (free key: https://fdc.nal.usda.gov/api-key-signup)
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Google Gemini (free key: https://aistudio.google.com/apikey)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Optional second model, tried when the main one is overloaded (HTTP 503).
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
# How much the model "thinks" before answering: minimal, low, medium, high (or empty for the
# model's default). Lower is much faster; a recipe does not need deep reasoning.
GEMINI_THINKING = os.getenv("GEMINI_THINKING", "").strip().lower()
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "90"))

# TheMealDB public test key "1" is allowed for development and education.
MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"
