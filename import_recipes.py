"""Fill the database with recipes from TheMealDB and calculate their nutrition.

    python import_recipes.py               # import up to 80 recipes
    python import_recipes.py --limit 150   # import more
    python import_recipes.py --recalculate # recalculate nutrition of all stored recipes
    python import_recipes.py --recalculate --refresh-usda
                                           # also forget old USDA matches and search again
"""
import argparse

from app import config
from app.database import get_db, init_db
from app.mealdb import import_meals
from app.recipes import recalculate


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=80, help="max number of new recipes (default 80)")
    parser.add_argument("--recalculate", action="store_true", help="recalculate nutrition for stored recipes")
    parser.add_argument("--refresh-usda", action="store_true", help="clear the USDA cache before recalculating")
    args = parser.parse_args()
    init_db()

    if config.USDA_API_KEY == "DEMO_KEY":
        print("Note: using USDA DEMO_KEY (very low rate limit). Put your own key in .env as USDA_API_KEY.")

    if args.refresh_usda:
        conn = get_db()
        conn.execute("DELETE FROM usda_cache")
        conn.commit()
        conn.close()
        print("USDA cache cleared; ingredients will be matched again.")

    if args.recalculate:
        conn = get_db()
        ids = [r[0] for r in conn.execute("SELECT id FROM recipes ORDER BY id")]
        conn.close()
        for i, rid in enumerate(ids, 1):
            result = recalculate(rid)
            print(f"  [{i}/{len(ids)}] recipe {rid} -> {result['category']}, {result['servings']} servings")
            for w in result["warnings"]:
                print(f"    warning: {w}")
        return

    print(f"Importing up to {args.limit} recipes from TheMealDB...")
    added = import_meals(limit=args.limit)
    print(f"Done. {added} new recipes added.")


if __name__ == "__main__":
    main()
