"""Recipe create / read / search / delete. Kept free of web-framework code."""
from app.database import get_db
from app.nutrition import FIELDS, calculate

SUMMARY_SQL = """
SELECT r.id, r.title, r.description, r.prep_time_min, r.servings, r.servings_estimated, r.category, r.meal_type,
       r.cuisine, r.image_url, r.source, r.created_at,
       n.calories, n.protein_g, n.carbs_g, n.fat_g, n.fiber_g, n.matched_count, n.total_count
FROM recipes r LEFT JOIN nutrition n ON n.recipe_id = r.id
"""


def _summary(row) -> dict:
    d = dict(row)
    d["nutrition"] = {f: d.pop(f) for f in FIELDS}
    d["nutrition"]["matched_count"] = d.pop("matched_count")
    d["nutrition"]["total_count"] = d.pop("total_count")
    return d


def _write_nutrition(conn, recipe_id: int, result: dict) -> None:
    conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    for ing in result["ingredients"]:
        conn.execute(
            "INSERT INTO ingredients (recipe_id, position, name, amount, grams, gram_method, fdc_id,"
            " usda_description, calories, protein_g, carbs_g, fat_g, fiber_g)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (recipe_id, ing["position"], ing["name"], ing["amount"], ing["grams"], ing["gram_method"],
             ing["fdc_id"], ing["usda_description"], *[ing[f] for f in FIELDS]),
        )
    p = result["per_serving"]
    conn.execute(
        "INSERT OR REPLACE INTO nutrition (recipe_id, calories, protein_g, carbs_g, fat_g, fiber_g,"
        " matched_count, total_count) VALUES (?,?,?,?,?,?,?,?)",
        (recipe_id, *[p[f] for f in FIELDS], result["matched_count"], result["total_count"]),
    )
    conn.execute("UPDATE recipes SET category = ?, servings = ?, servings_estimated = ? WHERE id = ?",
                 (result["category"], result["servings"], int(result["servings_estimated"]), recipe_id))


def create_recipe(data: dict, source: str = "user", source_ref: str = None) -> dict:
    servings = data.get("servings")   # None = unknown, estimated from the ingredients
    result = calculate(data.get("ingredients", []), servings)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO recipes (title, description, instructions, prep_time_min, servings, meal_type,"
        " cuisine, image_url, source, source_ref) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (data["title"].strip(), (data.get("description") or "").strip(), data["instructions"].strip(),
         data.get("prep_time_min"), result["servings"], data.get("meal_type") or "", data.get("cuisine") or "",
         data.get("image_url") or None, source, source_ref),
    )
    recipe_id = cur.lastrowid
    _write_nutrition(conn, recipe_id, result)
    conn.commit()
    conn.close()
    return {"id": recipe_id, "category": result["category"], "servings": result["servings"],
            "warnings": result["warnings"]}


def recalculate(recipe_id: int):
    conn = get_db()
    recipe = conn.execute("SELECT servings, servings_estimated FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if not recipe:
        conn.close()
        return None
    ings = [dict(r) for r in conn.execute(
        "SELECT name, amount FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,))]
    conn.close()
    result = calculate(ings, None if recipe["servings_estimated"] else recipe["servings"])
    conn = get_db()
    _write_nutrition(conn, recipe_id, result)
    conn.commit()
    conn.close()
    return {"id": recipe_id, "category": result["category"], "servings": result["servings"],
            "warnings": result["warnings"]}


def get_recipe(recipe_id: int):
    conn = get_db()
    row = conn.execute(SUMMARY_SQL + " WHERE r.id = ?", (recipe_id,)).fetchone()
    if not row:
        conn.close()
        return None
    recipe = _summary(row)
    recipe["instructions"] = conn.execute(
        "SELECT instructions FROM recipes WHERE id = ?", (recipe_id,)).fetchone()[0]
    recipe["ingredients"] = [dict(r) for r in conn.execute(
        "SELECT name, amount, grams, gram_method, fdc_id, usda_description, calories, protein_g,"
        " carbs_g, fat_g, fiber_g FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,))]
    conn.close()
    return recipe


def list_recipes(search: str = None, category: str = None, limit: int = 60, offset: int = 0) -> dict:
    where, params = [], []
    if search:
        for word in search.split():
            where.append("(r.title LIKE ? OR r.cuisine LIKE ? OR r.meal_type LIKE ? OR r.id IN "
                         "(SELECT recipe_id FROM ingredients WHERE name LIKE ?))")
            params += [f"%{word}%"] * 4
    if category:
        where.append("r.category = ?")
        params.append(category)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM recipes r" + clause, params).fetchone()[0]
    rows = conn.execute(SUMMARY_SQL + clause + " ORDER BY r.id DESC LIMIT ? OFFSET ?",
                        params + [limit, offset]).fetchall()
    conn.close()
    return {"total": total, "items": [_summary(r) for r in rows]}


def delete_recipe(recipe_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def categories() -> list:
    conn = get_db()
    rows = conn.execute("SELECT category, COUNT(*) AS count FROM recipes GROUP BY category"
                        " ORDER BY count DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_by_ingredients(names: list, limit: int = 6) -> list:
    """Stored recipes ranked by how many of the given ingredients they use."""
    names = [n.strip().lower() for n in names if n.strip()]
    if not names:
        return []
    score_sql = " + ".join(["MAX(CASE WHEN lower(i.name) LIKE ? THEN 1 ELSE 0 END)"] * len(names))
    conn = get_db()
    rows = conn.execute(
        f"SELECT i.recipe_id, ({score_sql}) AS hits FROM ingredients i GROUP BY i.recipe_id"
        " HAVING hits > 0 ORDER BY hits DESC, i.recipe_id DESC LIMIT ?",
        [f"%{n}%" for n in names] + [limit],
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        rec = get_recipe(r["recipe_id"])
        if rec:
            rec.pop("instructions", None)
            rec.pop("ingredients", None)
            rec["matched_ingredients"] = r["hits"]
            out.append(rec)
    return out
