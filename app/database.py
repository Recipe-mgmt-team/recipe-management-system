"""SQLite storage: recipes, their ingredients, per-serving nutrition and a USDA cache."""
import sqlite3

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    description   TEXT DEFAULT '',
    instructions  TEXT NOT NULL,
    prep_time_min INTEGER,
    servings      INTEGER NOT NULL DEFAULT 4,
    servings_estimated INTEGER NOT NULL DEFAULT 0,
    category      TEXT NOT NULL DEFAULT 'Uncategorized',
    meal_type     TEXT DEFAULT '',
    cuisine       TEXT DEFAULT '',
    image_url     TEXT,
    source        TEXT NOT NULL DEFAULT 'user',   -- user | ai | themealdb
    source_ref    TEXT,                           -- e.g. TheMealDB id
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredients (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id        INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position         INTEGER NOT NULL DEFAULT 0,
    name             TEXT NOT NULL,
    amount           TEXT DEFAULT '',
    grams            REAL DEFAULT 0,
    gram_method      TEXT DEFAULT '',
    fdc_id           INTEGER,
    usda_description TEXT,
    calories         REAL DEFAULT 0,
    protein_g        REAL DEFAULT 0,
    carbs_g          REAL DEFAULT 0,
    fat_g            REAL DEFAULT 0,
    fiber_g          REAL DEFAULT 0
);

-- Values are per serving.
CREATE TABLE IF NOT EXISTS nutrition (
    recipe_id     INTEGER PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE,
    calories      REAL NOT NULL DEFAULT 0,
    protein_g     REAL NOT NULL DEFAULT 0,
    carbs_g       REAL NOT NULL DEFAULT 0,
    fat_g         REAL NOT NULL DEFAULT 0,
    fiber_g       REAL NOT NULL DEFAULT 0,
    matched_count INTEGER NOT NULL DEFAULT 0,
    total_count   INTEGER NOT NULL DEFAULT 0
);

-- One row per looked-up ingredient name, so USDA is asked only once per food.
CREATE TABLE IF NOT EXISTS usda_cache (
    query         TEXT PRIMARY KEY,
    fdc_id        INTEGER,
    description   TEXT,
    data_type     TEXT,
    calories      REAL, protein_g REAL, carbs_g REAL, fat_g REAL, fiber_g REAL,
    measures_json TEXT,
    fetched_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ingredients_recipe ON ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recipes_source ON recipes(source, source_ref);
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript(SCHEMA)
    # Databases created by the first interim version lack this column.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(recipes)")]
    if "servings_estimated" not in cols:
        conn.execute("ALTER TABLE recipes ADD COLUMN servings_estimated INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE recipes SET servings_estimated = 1 WHERE source = 'themealdb'")
    conn.commit()
    conn.close()
