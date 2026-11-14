# Recipe Management System

CEN317 Engineering Design project, Çukurova University, Department of Computer Engineering.

A web application to store, search and add recipes, get recipe ideas from an LLM based on the
ingredients you have, and see nutrition values calculated from USDA FoodData Central.

## What works (interim version)

- Recipe list with search (name, ingredient, cuisine) and category filter
- Recipe detail with per-ingredient weight, USDA match and calories
- Add a recipe; nutrition is calculated on save ("Check nutrition" shows it before saving)
- "Ask AI": stored recipes that use your ingredients + one new recipe written by Google Gemini
- Recipes imported from TheMealDB (with photos)
- Calories, protein, carbs, fat and fiber are **calculated by code** from USDA FoodData Central,
  never estimated by the AI

## Setup

1. Python 3.10 or newer.
2. Get two free API keys:
   - USDA FoodData Central: https://fdc.nal.usda.gov/api-key-signup
   - Google Gemini: https://aistudio.google.com/apikey
3. Copy `.env.example` to `.env` and paste the keys in.
4. Install and fill the database:

```
pip install -r requirements.txt
python import_recipes.py --limit 80
python main.py
```

Open http://127.0.0.1:8000. On Windows you can just double-click `baslat.bat`.

`python import_recipes.py --recalculate` recomputes nutrition for all stored recipes
(useful if USDA was unreachable during import). Add `--refresh-usda` to forget old USDA
matches and search again after the matching rules change (or double-click `yeniden_hesapla.bat`).

TheMealDB does not give serving counts, so for imported recipes the number of servings is
estimated from the total ingredient weight (about 450 g per serving, 2 to 10 servings).

## Project structure

```
main.py             FastAPI app: REST API + serves the web page
import_recipes.py   CLI: import recipes from TheMealDB / recalculate nutrition
app/
  config.py         settings from .env
  database.py       SQLite schema
  recipes.py        create / read / search / delete recipes
  nutrition.py      nutrition calculation and category rules
  usda.py           USDA FoodData Central search, best-match selection, cache
  units.py          amount text -> grams ("1 1/2 cups", "400g can", "2 cloves")
  ai_service.py     Google Gemini recipe suggestions
  mealdb.py         TheMealDB importer
static/             index.html, style.css, app.js (plain JavaScript)
tests/              unit tests (offline): python -m unittest discover tests
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /api/recipes?search=&category=&limit=&offset= | list / search recipes |
| GET | /api/recipes/{id} | recipe detail |
| POST | /api/recipes | add a recipe (nutrition calculated) |
| POST | /api/recipes/{id}/recalculate | recalculate nutrition |
| DELETE | /api/recipes/{id} | delete a recipe |
| GET | /api/categories | categories with counts |
| POST | /api/nutrition/preview | calculate nutrition without saving |
| POST | /api/ai/suggest | matching recipes + Gemini suggestion |
| POST | /api/ai/save | save an AI suggestion |
| GET | /api/status | key / model status |

Interactive docs: http://127.0.0.1:8000/docs

## Data sources

- Recipes: [TheMealDB](https://www.themealdb.com) (free test key, for development/education)
- Nutrition: [USDA FoodData Central](https://fdc.nal.usda.gov) (Foundation and SR Legacy datasets)
- Suggestions: Google Gemini API

## License

MIT
