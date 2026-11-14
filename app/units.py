"""Turn free-text amounts ("1 1/2 cups", "400g can", "2 cloves") into grams.

Order of preference:
1. Mass units (g, kg, oz, lb) are converted exactly.
2. Household units (cup, tbsp, clove, large ...) use the USDA portion weights
   of the matched food ("foodMeasures") when USDA has one for that unit.
3. Otherwise a generic conversion table is used (documented assumptions).
"""
import re
from typing import Optional

UNICODE_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}

# unit alias -> canonical unit
UNIT_ALIASES = {
    "g": "g", "gr": "g", "gm": "g", "gram": "g", "grams": "g", "grammes": "g",
    "kg": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
    "mg": "mg",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml", "millilitres": "ml", "milliliters": "ml",
    "cl": "cl", "dl": "dl",
    "l": "l", "litre": "l", "liter": "l", "litres": "l", "liters": "l",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp", "tsps": "tsp",
    "tbsp": "tbsp", "tbs": "tbsp", "tblsp": "tbsp", "tbls": "tbsp", "tablespoon": "tbsp",
    "tablespoons": "tbsp", "tbsps": "tbsp",
    "cup": "cup", "cups": "cup",
    "pinch": "pinch", "pinches": "pinch", "dash": "pinch",
    "clove": "clove", "cloves": "clove",
    "slice": "slice", "slices": "slice",
    "can": "can", "cans": "can", "tin": "can", "tins": "can",
    "handful": "handful", "handfuls": "handful",
    "bunch": "bunch", "bunches": "bunch",
    "sprig": "sprig", "sprigs": "sprig",
    "stick": "stick", "sticks": "stick",
    "large": "large", "medium": "medium", "small": "small",
    "piece": "piece", "pieces": "piece", "whole": "piece",
}

# Generic grams per unit (water density assumed for volumes).
GENERIC_GRAMS = {
    "g": 1, "kg": 1000, "mg": 0.001, "oz": 28.35, "lb": 453.6,
    "ml": 1, "cl": 10, "dl": 100, "l": 1000,
    "tsp": 5, "tbsp": 15, "cup": 240, "pinch": 0.4,
    "clove": 3, "slice": 30, "can": 400, "handful": 30, "bunch": 50,
    "sprig": 1, "stick": 113,
}

# Typical weight of one item when only a count is given ("2 onions").
PIECE_GRAMS = {
    "egg": 50, "onion": 110, "shallot": 40, "tomato": 120, "potato": 170,
    "carrot": 60, "lemon": 60, "lime": 45, "orange": 140, "apple": 180,
    "banana": 120, "pepper": 120, "chilli": 15, "chili": 15, "courgette": 200,
    "zucchini": 200, "aubergine": 300, "eggplant": 300, "cucumber": 300,
    "avocado": 150, "chicken breast": 170, "chicken thigh": 110, "garlic": 3,
    "bay leaf": 0.2, "bay leaves": 0.2, "tortilla": 45, "bread": 30, "bun": 60,
}
DEFAULT_PIECE_GRAMS = 100

# Units that USDA portion descriptions use for each canonical unit.
MEASURE_KEYWORDS = {
    "cup": ["cup"], "tbsp": ["tbsp", "tablespoon"], "tsp": ["tsp", "teaspoon"],
    "clove": ["clove"], "slice": ["slice"], "large": ["large"], "medium": ["medium"],
    "small": ["small"], "piece": ["medium", "whole", "piece", "fruit", "item"],
    "stick": ["stick"], "can": ["can"],
}

NOT_MEASURED = ("to taste", "to serve", "garnish", "for frying", "as required", "as needed", "optional")

_NUM = r"(\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?|[½¼¾⅓⅔⅛])"


def _to_float(token: str) -> float:
    token = token.strip()
    if token in UNICODE_FRACTIONS:
        return UNICODE_FRACTIONS[token]
    if " " in token:  # mixed number "1 1/2"
        whole, frac = token.split()
        return float(whole) + _to_float(frac)
    if "/" in token:
        a, b = token.split("/")
        return float(a) / float(b) if float(b) else 0.0
    return float(token.replace(",", "."))


def parse_amount(text: str):
    """Return (quantity, canonical_unit or None). quantity is None when no number."""
    if not text:
        return None, None
    t = text.lower().strip()
    # "1½" -> "1 ½"
    t = re.sub(r"(\d)([½¼¾⅓⅔⅛])", r"\1 \2", t)
    for ch, val in UNICODE_FRACTIONS.items():
        t = re.sub(rf"(\d+)\s+{ch}", lambda m: str(int(m.group(1)) + val), t)

    # "2 x 400g tins" -> multiplier 2
    multiplier = 1.0
    m = re.match(rf"^\s*{_NUM}\s*x\s*(.*)$", t)
    if m:
        multiplier = _to_float(m.group(1))
        t = m.group(2)

    m = re.search(_NUM, t)
    if not m:
        word_unit = _find_unit(t)
        if word_unit in ("pinch",):
            return 1.0, word_unit
        return None, word_unit
    qty = _to_float(m.group(1)) * multiplier
    rest = t[m.end():]
    # ranges like "2-3" -> keep the first number
    rest = re.sub(rf"^\s*(-|to)\s*{_NUM}", "", rest)
    return qty, _find_unit(rest)


def _find_unit(rest: str) -> Optional[str]:
    words = re.findall(r"[a-zA-Z]+", rest)
    for w in words[:3]:
        if w in UNIT_ALIASES:
            return UNIT_ALIASES[w]
    return None


def _measure_grams(unit: str, measures: list) -> Optional[float]:
    """Find grams for one `unit` in the USDA portion list of a food."""
    keys = MEASURE_KEYWORDS.get(unit)
    if not keys or not measures:
        return None
    for key in keys:
        for ms in measures:
            label = (ms.get("text") or "").lower()
            if re.search(rf"\b{key}", label) and ms.get("grams"):
                m = re.match(rf"^\s*{_NUM}", label)
                count = _to_float(m.group(1)) if m else 1.0
                return float(ms["grams"]) / (count or 1.0)
    return None


def to_grams(amount: str, ingredient_name: str, measures: Optional[list] = None):
    """Return (grams, method) where method explains how the number was found."""
    text = (amount or "").lower()
    if any(p in text for p in NOT_MEASURED) and not re.search(r"\d", text):
        return 0.0, "not measured"
    qty, unit = parse_amount(amount)
    if qty is None:
        qty = 1.0 if (unit or text.strip() == "") else None
        if qty is None:
            return 0.0, "not measured"

    if unit in ("g", "kg", "mg", "oz", "lb"):
        return qty * GENERIC_GRAMS[unit], "mass unit"

    usda = _measure_grams(unit or "piece", measures or [])
    if usda:
        return qty * usda, "USDA portion"

    if unit in GENERIC_GRAMS:
        return qty * GENERIC_GRAMS[unit], "generic table"

    name = (ingredient_name or "").lower()
    for key, grams in PIECE_GRAMS.items():
        if key in name:
            factor = {"large": 1.25, "small": 0.75}.get(unit, 1.0)
            return qty * grams * factor, "typical piece weight"
    return qty * DEFAULT_PIECE_GRAMS, "default piece weight"
