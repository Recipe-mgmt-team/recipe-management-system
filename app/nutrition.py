"""Recipe nutrition = sum over ingredients of (grams / 100) x (USDA value per 100 g).

The LLM is never asked for calories: every number here comes from USDA data
and the unit conversion in units.py.
"""
from concurrent.futures import ThreadPoolExecutor

from app import usda
from app.units import to_grams

FIELDS = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")

# Imported recipes do not say how many people they serve. We estimate it from the
# total weight of food, assuming about 450 g per serving, limited to 2-10 servings.
GRAMS_PER_SERVING = 450
MIN_SERVINGS, MAX_SERVINGS = 2, 10


def estimate_servings(rows: list) -> int:
    food_grams = sum(r["grams"] for r in rows if "water" not in r["name"].lower())
    return max(MIN_SERVINGS, min(MAX_SERVINGS, round(food_grams / GRAMS_PER_SERVING)))


def categorize(per_serving: dict, matched: int, total: int) -> str:
    """Rule-based category from per-serving values (thresholds in the report, Table 3.2)."""
    if total == 0 or matched / total < 0.5:
        return "Uncategorized"
    kcal, carbs = per_serving["calories"], per_serving["carbs_g"]
    protein, fat = per_serving["protein_g"], per_serving["fat_g"]
    if carbs <= 12 and fat >= 18:
        return "Keto-friendly"
    if protein >= 28:
        return "High protein"
    if carbs <= 18:
        return "Low carb"
    if kcal <= 380:
        return "Low calorie"
    if kcal >= 750:
        return "High energy"
    return "Balanced"


def calculate(ingredients: list, servings=None) -> dict:
    """ingredients: [{"name": str, "amount": str}, ...]
    servings=None means "unknown": it is estimated from the total weight."""
    rows, totals, warnings = [], {f: 0.0 for f in FIELDS}, []
    matched = counted = 0

    def safe_lookup(name):
        try:
            return usda.lookup(name), None
        except usda.UsdaError as e:
            return None, str(e)

    # Ask USDA about all ingredients at the same time instead of one after another.
    names = [(ing.get("name") or "").strip() for ing in ingredients]
    with ThreadPoolExecutor(max_workers=6) as pool:
        found = list(pool.map(lambda n: safe_lookup(n) if n else (None, None), names))

    for pos, ing in enumerate(ingredients):
        name = names[pos]
        amount = (ing.get("amount") or "").strip()
        if not name:
            continue
        row = {"position": pos, "name": name, "amount": amount, "grams": 0.0, "gram_method": "",
               "fdc_id": None, "usda_description": None, **{f: 0.0 for f in FIELDS}}
        food, error = found[pos]
        if error and error not in warnings:
            warnings.append(error)

        grams, method = to_grams(amount, name, food["measures"] if food else None)
        row["grams"], row["gram_method"] = round(grams, 1), method
        if grams > 0:
            counted += 1
        if food:
            row["fdc_id"], row["usda_description"] = food["fdc_id"], food["description"]
            for f in FIELDS:
                row[f] = round(food["per_100g"][f] * grams / 100, 2)
                totals[f] += food["per_100g"][f] * grams / 100
            if grams > 0:
                matched += 1
        rows.append(row)

    estimated = not servings
    servings = estimate_servings(rows) if estimated else max(int(servings), 1)
    per_serving = {f: round(totals[f] / servings, 1) for f in FIELDS}
    return {
        "servings": servings,
        "servings_estimated": estimated,
        "ingredients": rows,
        "per_serving": per_serving,
        "matched_count": matched,
        "total_count": counted,
        "category": categorize(per_serving, matched, counted),
        "warnings": warnings,
    }
