"""Match ingredient names to foods in USDA FoodData Central (FDC).

Only the "Foundation" and "SR Legacy" datasets are searched: they describe
generic foods (e.g. "Onions, raw") with nutrient values per 100 g, which is
what a recipe calculator needs. Branded products are skipped on purpose.
"""
import json
import re

import requests

from app import config
from app.database import get_db

# FDC nutrient ids
ENERGY_KCAL = 1008
ENERGY_ATWATER_GENERAL = 2047
ENERGY_ATWATER_SPECIFIC = 2048
PROTEIN, FAT, CARBS, FIBER = 1003, 1004, 1005, 1079

# Recipe sites use everyday names; USDA uses "Category, detail, state".
# These rewrites make the search hit the right generic food.
QUERY_ALIASES = {
    "plain flour": "wheat flour white all-purpose enriched",
    "flour": "wheat flour white all-purpose enriched",
    "self-raising flour": "wheat flour white self-rising",
    "olive oil": "oil olive salad or cooking",
    "extra virgin olive oil": "oil olive salad or cooking",
    "vegetable oil": "oil vegetable soybean",
    "sunflower oil": "oil sunflower",
    "salt": "salt table",
    "sea salt": "salt table",
    "pepper": "spices pepper black",
    "black pepper": "spices pepper black",
    "butter": "butter salted",
    "unsalted butter": "butter without salt",
    "egg": "egg whole raw fresh",
    "eggs": "egg whole raw fresh",
    "egg yolks": "egg yolk raw fresh",
    "egg white": "egg white raw fresh",
    "sugar": "sugars granulated",
    "caster sugar": "sugars granulated",
    "brown sugar": "sugars brown",
    "icing sugar": "sugars powdered",
    "milk": "milk whole 3.25%",
    "water": "water tap drinking",
    "chicken": "chicken broilers or fryers meat only raw",
    "chicken breast": "chicken broiler breast meat only raw",
    "chicken breasts": "chicken broiler breast meat only raw",
    "chicken thighs": "chicken broilers thigh meat only raw",
    "beef": "beef ground 80% lean meat raw",
    "minced beef": "beef ground 80% lean meat raw",
    "ground beef": "beef ground 80% lean meat raw",
    "lamb": "lamb ground raw",
    "rice": "rice white long-grain regular raw enriched",
    "basmati rice": "rice white long-grain regular raw enriched",
    "tomato": "tomatoes red ripe raw",
    "tomatoes": "tomatoes red ripe raw",
    "chopped tomatoes": "tomatoes red ripe canned",
    "tinned tomatoes": "tomatoes red ripe canned",
    "tomato puree": "tomato products canned puree",
    "potatoes": "potatoes flesh and skin raw",
    "potato": "potatoes flesh and skin raw",
    "carrots": "carrots raw",
    "carrot": "carrots raw",
    "onion": "onions raw",
    "onions": "onions raw",
    "red onion": "onions raw",
    "red onions": "onions raw",
    "spring onions": "onions spring or scallions raw",
    "garlic": "garlic raw",
    "garlic clove": "garlic raw",
    "ginger": "ginger root raw",
    "lemon": "lemons raw without peel",
    "lemon juice": "lemon juice raw",
    "lime": "limes raw",
    "lime juice": "lime juice raw",
    "parmesan": "cheese parmesan grated",
    "parmesan cheese": "cheese parmesan grated",
    "cheddar cheese": "cheese cheddar",
    "mozzarella": "cheese mozzarella whole milk",
    "double cream": "cream fluid heavy whipping",
    "heavy cream": "cream fluid heavy whipping",
    "single cream": "cream fluid light",
    "coriander": "coriander cilantro leaves raw",
    "cilantro": "coriander cilantro leaves raw",
    "parsley": "parsley fresh",
    "spaghetti": "pasta dry enriched",
    "pasta": "pasta dry enriched",
    "penne rigate": "pasta dry enriched",
    "chicken stock": "soup stock chicken home-prepared",
    "beef stock": "soup stock beef home-prepared",
    "vegetable stock": "soup vegetable broth",
    "soy sauce": "soy sauce made from soy",
    "honey": "honey",
    "greek yogurt": "yogurt greek plain whole milk",
    "yogurt": "yogurt plain whole milk",
    "chickpeas": "chickpeas garbanzo beans mature seeds canned",
    "kidney beans": "beans kidney red mature seeds canned",
    "lentils": "lentils raw",
    "red pepper": "peppers sweet red raw",
    "green pepper": "peppers sweet green raw",
    "mushrooms": "mushrooms white raw",
    "cumin": "spices cumin seed",
    "paprika": "spices paprika",
    "chili powder": "spices chili powder",
    "chili peppers": "peppers hot chili red raw",
    "chili": "peppers hot chili red raw",
    "red chili": "peppers hot chili red raw",
    "green chili": "peppers hot chili green raw",
    "chili flakes": "spices pepper red or cayenne",
    "cayenne pepper": "spices pepper red or cayenne",
    "cinnamon": "spices cinnamon ground",
    "turmeric": "spices turmeric ground",
    "oregano": "spices oregano dried",
    "bread": "bread white commercially prepared",
    "baking powder": "leavening agents baking powder double-acting",
}

PREFERRED_TYPES = ["Foundation", "SR Legacy"]

# British spellings used by TheMealDB -> the American spellings used by USDA.
UK_TO_US = {
    "chilli": "chili", "chillies": "chili peppers", "chilies": "chili peppers",
    "courgette": "zucchini", "courgettes": "zucchini", "aubergine": "eggplant", "aubergines": "eggplant",
    "minced": "ground", "mince": "ground beef", "coriander": "coriander", "rocket": "arugula",
    "yoghurt": "yogurt", "prawns": "shrimp", "prawn": "shrimp", "beetroot": "beets",
    "spring onion": "spring onions", "caster": "granulated", "icing": "powdered",
}

# Words that describe a form or state, not the food itself. A match on these words
# alone is not enough (otherwise "chilli powder" matched "Baobab powder").
GENERIC_WORDS = {
    "powder", "sauce", "oil", "juice", "fresh", "dried", "dry", "ground", "chopped", "sliced",
    "raw", "whole", "paste", "stock", "leaves", "leaf", "seeds", "seed", "flakes", "red", "green",
    "white", "black", "yellow", "large", "small", "medium", "plain", "canned", "frozen", "cooked",
    "boneless", "skinless", "extra", "virgin", "fine", "sweet", "hot", "mixed", "baby",
}


class UsdaError(Exception):
    pass


def normalize(name: str) -> str:
    name = (name or "").lower().strip()
    name = re.sub(r"\(.*?\)", "", name)          # drop "(optional)" etc.
    name = re.sub(r"[^a-z0-9%\- ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    for uk, us in UK_TO_US.items():
        name = re.sub(rf"\b{uk}\b", us, name)
    return name


def _nutrient_map(food: dict) -> dict:
    values = {}
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        unit = (n.get("unitName") or "").upper()
        if nid in (ENERGY_KCAL, ENERGY_ATWATER_GENERAL, ENERGY_ATWATER_SPECIFIC) and unit != "KCAL":
            continue
        if n.get("value") is not None:
            values[nid] = float(n["value"])
    protein = values.get(PROTEIN, 0.0)
    fat = values.get(FAT, 0.0)
    carbs = values.get(CARBS, 0.0)
    kcal = next((values[k] for k in (ENERGY_KCAL, ENERGY_ATWATER_GENERAL, ENERGY_ATWATER_SPECIFIC)
                 if k in values), None)
    if kcal is None:
        if not (protein or fat or carbs):
            return {}
        kcal = 4 * protein + 4 * carbs + 9 * fat   # Atwater general factors
    return {"calories": kcal, "protein_g": protein, "carbs_g": carbs,
            "fat_g": fat, "fiber_g": values.get(FIBER, 0.0)}


def _score(query: str, food: dict) -> float:
    """Higher is better. Rewards descriptions that contain the query words."""
    desc = (food.get("description") or "").lower()
    words = [w for w in re.findall(r"[a-z]+", query) if len(w) > 2]
    if not words:
        return 0.0
    def hit(w):
        return w in desc or w.rstrip("s") in desc
    specific = [w for w in words if w not in GENERIC_WORDS]
    if specific and not any(hit(w) for w in specific):
        return 0.0                      # only generic words matched: not the same food
    hits = sum(1 for w in words if hit(w))
    score = 10.0 * hits / len(words)
    first = desc.split(",")[0]
    if any(w.rstrip("s") in first for w in (specific or words)):
        score += 3                      # main word is the food itself, not a side note
    if "raw" in desc and not any(w in query for w in ("cooked", "boiled", "roasted", "fried")):
        score += 1
    if food.get("dataType") == "SR Legacy":
        score += 0.5                    # has household portion weights
    score -= len(desc) / 120            # prefer plain, generic descriptions
    return score


def pick_best(query: str, foods: list):
    candidates = []
    for f in foods:
        if f.get("dataType") not in PREFERRED_TYPES:
            continue
        nutrients = _nutrient_map(f)
        if not nutrients:
            continue
        candidates.append((_score(query, f), f, nutrients))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    score, food, nutrients = candidates[0]
    if score < 5:          # fewer than half of the words matched: treat as no match
        return None
    measures = [
        {"text": m.get("disseminationText", ""), "grams": m.get("gramWeight")}
        for m in food.get("foodMeasures", []) if m.get("gramWeight")
    ]
    return {
        "fdc_id": food.get("fdcId"),
        "description": food.get("description"),
        "data_type": food.get("dataType"),
        "per_100g": nutrients,
        "measures": measures,
    }


def search_fdc(query: str) -> list:
    try:
        resp = requests.post(
            config.USDA_SEARCH_URL,
            params={"api_key": config.USDA_API_KEY},
            json={"query": query, "dataType": PREFERRED_TYPES, "pageSize": 25},
            timeout=12,
        )
    except requests.RequestException as e:
        raise UsdaError(f"Could not reach USDA FoodData Central: {e}") from e
    if resp.status_code == 429:
        raise UsdaError("USDA rate limit reached. Get a free personal key and put it in .env as USDA_API_KEY.")
    if resp.status_code == 403:
        raise UsdaError("USDA rejected the API key. Check USDA_API_KEY in .env.")
    if resp.status_code != 200:
        raise UsdaError(f"USDA returned HTTP {resp.status_code}")
    return resp.json().get("foods", [])


def lookup(name: str):
    """Return the USDA match for an ingredient name, using the cache first.

    Returns None when USDA has no reasonable match. Raises UsdaError when
    USDA cannot be asked (network, key, rate limit); such misses are not cached.
    """
    key = normalize(name)
    if not key:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM usda_cache WHERE query = ?", (key,)).fetchone()
    if row:
        conn.close()
        if row["fdc_id"] is None:
            return None
        return {
            "fdc_id": row["fdc_id"], "description": row["description"], "data_type": row["data_type"],
            "per_100g": {k: row[k] for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")},
            "measures": json.loads(row["measures_json"] or "[]"),
        }
    conn.close()

    query = QUERY_ALIASES.get(key, key)
    match = pick_best(query, search_fdc(query))
    if match is None and query != key:
        match = pick_best(key, search_fdc(key))

    conn = get_db()
    if match:
        p = match["per_100g"]
        conn.execute(
            "INSERT OR REPLACE INTO usda_cache (query, fdc_id, description, data_type, calories, protein_g,"
            " carbs_g, fat_g, fiber_g, measures_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (key, match["fdc_id"], match["description"], match["data_type"], p["calories"],
             p["protein_g"], p["carbs_g"], p["fat_g"], p["fiber_g"], json.dumps(match["measures"])),
        )
    else:
        conn.execute("INSERT OR REPLACE INTO usda_cache (query) VALUES (?)", (key,))
    conn.commit()
    conn.close()
    return match
