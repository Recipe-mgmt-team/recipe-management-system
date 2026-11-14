"""Import recipes from TheMealDB (https://www.themealdb.com), a free open recipe API."""
import re
import string
import time

import requests

from app import config
from app.database import get_db
from app.recipes import create_recipe


def fetch_letter(letter: str) -> list:
    resp = requests.get(f"{config.MEALDB_BASE_URL}/search.php", params={"f": letter}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("meals") or []


def to_recipe(meal: dict) -> dict:
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "amount": (meal.get(f"strMeasure{i}") or "").strip()})
    steps = [s.strip() for s in re.split(r"\r?\n", meal.get("strInstructions") or "") if s.strip()]
    steps = [s for s in steps if not re.fullmatch(r"(step\s*)?\d+\.?", s, flags=re.I)]
    area, category = meal.get("strArea") or "", meal.get("strCategory") or ""
    return {
        "title": meal["strMeal"].strip(),
        "description": f"{area} {category.lower()} recipe.".strip() if area or category else "",
        "instructions": "\n".join(steps),
        "servings": None,          # not given by TheMealDB: estimated from the ingredients
        "prep_time_min": None,
        "meal_type": category,
        "cuisine": area,
        "image_url": meal.get("strMealThumb"),
        "ingredients": ingredients,
    }


def already_imported(meal_id: str) -> bool:
    conn = get_db()
    row = conn.execute("SELECT 1 FROM recipes WHERE source='themealdb' AND source_ref=?", (meal_id,)).fetchone()
    conn.close()
    return row is not None


def import_meals(limit: int = 80, letters: str = string.ascii_lowercase, log=print) -> int:
    added = 0
    for letter in letters:
        if added >= limit:
            break
        try:
            meals = fetch_letter(letter)
        except requests.RequestException as e:
            log(f"  could not fetch letter '{letter}': {e}")
            continue
        for meal in meals:
            if added >= limit:
                break
            if already_imported(meal["idMeal"]):
                continue
            result = create_recipe(to_recipe(meal), source="themealdb", source_ref=meal["idMeal"])
            added += 1
            log(f"  [{added}/{limit}] {meal['strMeal']} -> {result['category']}, {result['servings']} servings")
            for w in result["warnings"]:
                log(f"    warning: {w}")
        time.sleep(0.3)   # be polite to the free API
    return added
