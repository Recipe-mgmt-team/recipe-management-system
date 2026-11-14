"""Run with:  python -m unittest discover tests
USDA answers are faked here, so the tests work offline."""
import os
import tempfile
import unittest

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from app import usda                          # noqa: E402
from app.database import init_db              # noqa: E402
from app.nutrition import calculate, categorize  # noqa: E402
from app import recipes                        # noqa: E402
from app.units import parse_amount, to_grams   # noqa: E402


def food(fdc_id, desc, kcal, p, c, f, fiber=0, dtype="SR Legacy", measures=()):
    return {"fdcId": fdc_id, "description": desc, "dataType": dtype,
            "foodNutrients": [
                {"nutrientId": 1008, "unitName": "KCAL", "value": kcal},
                {"nutrientId": 1062, "unitName": "kJ", "value": kcal * 4.184},
                {"nutrientId": 1003, "unitName": "G", "value": p},
                {"nutrientId": 1005, "unitName": "G", "value": c},
                {"nutrientId": 1004, "unitName": "G", "value": f},
                {"nutrientId": 1079, "unitName": "G", "value": fiber}],
            "foodMeasures": [{"disseminationText": t, "gramWeight": g} for t, g in measures]}


FAKE_DB = {
    "egg whole raw fresh": [food(171287, "Egg, whole, raw, fresh", 143, 12.6, 0.7, 9.5, measures=[("1 large", 50)])],
    "onions raw": [food(170000, "Onions, raw", 40, 1.1, 9.3, 0.1, 1.7, measures=[("1 medium", 110), ("1 cup, chopped", 160)]),
                   food(170001, "Onion rings, breaded, frozen", 280, 3, 30, 15)],
    "oil olive salad or cooking": [food(171413, "Oil, olive, salad or cooking", 884, 0, 0, 100, measures=[("1 tbsp", 13.5)])],
    "salt table": [food(173468, "Salt, table", 0, 0, 0, 0)],
    "chicken broiler breast meat only raw": [food(171077, "Chicken, broilers or fryers, breast, meat only, raw", 120, 22.5, 0, 2.6)],
    "unobtainium": [food(1, "Cookies, chocolate chip", 480, 5, 65, 22)],
    "spices chili powder": [food(167806, "Baobab powder", 250, 2, 80, 1),
                            food(171319, "Spices, chili powder", 282, 13.5, 49.7, 14.3)],
    "lentils raw": [food(172420, "Lentils, raw", 352, 24.6, 63.4, 1.1)],
}
calls = []


def fake_search(query):
    calls.append(query)
    return FAKE_DB.get(query, [])


usda.search_fdc = fake_search
init_db()


class UnitTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_amount("1 1/2 cups"), (1.5, "cup"))
        self.assertEqual(parse_amount("½ tsp"), (0.5, "tsp"))
        self.assertEqual(parse_amount("1½ tbsp"), (1.5, "tbsp"))
        self.assertEqual(parse_amount("400g can"), (400, "g"))
        self.assertEqual(parse_amount("2 x 400g tins"), (800, "g"))
        self.assertEqual(parse_amount("2-3 cloves"), (2, "clove"))
        self.assertEqual(parse_amount("To taste"), (None, None))

    def test_grams(self):
        self.assertEqual(to_grams("1 lb", "beef")[0], 453.6)
        self.assertEqual(to_grams("to taste", "salt"), (0.0, "not measured"))
        self.assertEqual(to_grams("2", "eggs")[0], 100)        # typical piece weight
        self.assertEqual(to_grams("1 cup", "onion", [{"text": "1 cup, chopped", "grams": 160}]), (160, "USDA portion"))
        self.assertEqual(to_grams("2 tbsp", "olive oil")[0], 30)
        self.assertEqual(to_grams("3 large", "eggs", [{"text": "1 large", "grams": 50}])[0], 150)


class NutritionTests(unittest.TestCase):
    def test_lookup_picks_generic_food_and_caches(self):
        m = usda.lookup("Onions")
        self.assertEqual(m["description"], "Onions, raw")
        n = len(calls)
        usda.lookup("onions")
        self.assertEqual(len(calls), n)                       # served from cache

    def test_bad_match_rejected(self):
        self.assertIsNone(usda.lookup("unobtainium"))

    def test_zero_kcal_food_is_a_match(self):
        self.assertEqual(usda.lookup("salt")["per_100g"]["calories"], 0)

    def test_calculate(self):
        r = calculate([{"name": "chicken breast", "amount": "200g"},
                       {"name": "olive oil", "amount": "1 tbsp"},
                       {"name": "salt", "amount": "to taste"}], servings=2)
        # chicken 200 g -> 240 kcal; oil 13.5 g (USDA portion) -> 119.3 kcal; total / 2
        self.assertAlmostEqual(r["per_serving"]["calories"], (240 + 884 * 0.135) / 2, places=0)
        self.assertEqual(r["matched_count"], 2)
        self.assertEqual(r["total_count"], 2)

    def test_british_spelling_and_generic_words(self):
        # "chilli" -> "chili"; "Baobab powder" shares only the generic word "powder"
        self.assertEqual(usda.lookup("Chilli Powder")["description"], "Spices, chili powder")
        self.assertEqual(usda._score("spices chili powder", {"description": "Baobab powder"}), 0.0)

    def test_servings_estimated_when_unknown(self):
        r = calculate([{"name": "lentils", "amount": "2 kg"}, {"name": "water", "amount": "1 l"}], servings=None)
        self.assertTrue(r["servings_estimated"])
        self.assertEqual(r["servings"], 4)              # 2000 g / 450 g, water ignored
        small = calculate([{"name": "lentils", "amount": "100 g"}], servings=None)
        self.assertEqual(small["servings"], 2)          # lower limit
        given = calculate([{"name": "lentils", "amount": "2 kg"}], servings=3)
        self.assertEqual((given["servings"], given["servings_estimated"]), (3, False))

    def test_categorize(self):
        self.assertEqual(categorize({"calories": 300, "protein_g": 35, "carbs_g": 20, "fat_g": 5}, 3, 3), "High protein")
        self.assertEqual(categorize({"calories": 300, "protein_g": 35, "carbs_g": 20, "fat_g": 5}, 1, 4), "Uncategorized")


class RepositoryTests(unittest.TestCase):
    def test_imported_recipe_gets_estimated_servings(self):
        rid = recipes.create_recipe({"title": "Big lentil pot", "instructions": "1. Cook.", "servings": None,
                                     "ingredients": [{"name": "lentils", "amount": "3 kg"}]},
                                    source="themealdb", source_ref="t1")["id"]
        r = recipes.get_recipe(rid)
        self.assertEqual((r["servings"], r["servings_estimated"]), (7, 1))
        self.assertEqual(recipes.recalculate(rid)["servings"], 7)

    def test_create_search_detail_delete(self):
        res = recipes.create_recipe({"title": "Simple omelette", "instructions": "1. Beat.\n2. Cook.",
                                     "servings": 1, "ingredients": [{"name": "eggs", "amount": "3 large"},
                                                                    {"name": "onion", "amount": "1"}]})
        rid = res["id"]
        detail = recipes.get_recipe(rid)
        self.assertEqual(len(detail["ingredients"]), 2)
        self.assertAlmostEqual(detail["nutrition"]["calories"], 143 * 1.5 + 44, places=0)
        self.assertEqual(recipes.list_recipes(search="omelette")["total"], 1)
        self.assertEqual(recipes.list_recipes(search="onion")["total"], 1)   # ingredient search
        self.assertEqual(recipes.find_by_ingredients(["egg", "onion"])[0]["matched_ingredients"], 2)
        self.assertTrue(recipes.delete_recipe(rid))
        self.assertIsNone(recipes.get_recipe(rid))


if __name__ == "__main__":
    unittest.main()
