"""Recipe Management System - FastAPI server (REST API + static web page)."""
import os
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import ai_service, config, recipes
from app.database import get_db, init_db
from app.nutrition import calculate

app = FastAPI(title="Recipe Management System API", version="0.4.0")
STATIC_DIR = os.path.join(config.BASE_DIR, "static")


@app.on_event("startup")
def startup() -> None:
    init_db()


class Ingredient(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Optional[str] = ""


class RecipeIn(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: Optional[str] = ""
    instructions: str = Field(min_length=5)
    servings: int = Field(default=2, ge=1, le=50)
    prep_time_min: Optional[int] = Field(default=None, ge=0, le=1440)
    meal_type: Optional[str] = ""
    cuisine: Optional[str] = ""
    image_url: Optional[str] = None
    ingredients: List[Ingredient] = Field(min_length=1)


class NutritionPreviewIn(BaseModel):
    servings: int = Field(default=2, ge=1, le=50)
    ingredients: List[Ingredient]


class SuggestIn(BaseModel):
    ingredients: List[str] = Field(min_length=1)
    notes: Optional[str] = ""


# ---------- recipes ----------

@app.get("/api/recipes")
def list_recipes(search: Optional[str] = None, category: Optional[str] = None,
                 limit: int = 60, offset: int = 0):
    return recipes.list_recipes(search, category, min(max(limit, 1), 200), max(offset, 0))


@app.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    recipe = recipes.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found.")
    return recipe


@app.post("/api/recipes", status_code=201)
def add_recipe(data: RecipeIn):
    return recipes.create_recipe(data.model_dump(), source="user")


@app.post("/api/recipes/{recipe_id}/recalculate")
def recalculate(recipe_id: int):
    result = recipes.recalculate(recipe_id)
    if not result:
        raise HTTPException(404, "Recipe not found.")
    return result


@app.delete("/api/recipes/{recipe_id}")
def delete_recipe(recipe_id: int):
    if not recipes.delete_recipe(recipe_id):
        raise HTTPException(404, "Recipe not found.")
    return {"deleted": recipe_id}


@app.get("/api/categories")
def categories():
    return recipes.categories()


# ---------- nutrition ----------

@app.post("/api/nutrition/preview")
def nutrition_preview(data: NutritionPreviewIn):
    """Calculate nutrition for an ingredient list without saving anything."""
    return calculate([i.model_dump() for i in data.ingredients], data.servings)


# ---------- AI suggestions ----------

@app.post("/api/ai/matches")
def ai_matches(data: SuggestIn):
    """Only the stored recipes that use the ingredients (fast, no AI)."""
    return recipes.find_by_ingredients([n for n in data.ingredients if n.strip()])


@app.post("/api/ai/suggest")
def ai_suggest(data: SuggestIn):
    """Stored recipes that use the ingredients + one new recipe written by Gemini."""
    names = [n.strip() for n in data.ingredients if n.strip()]
    if not names:
        raise HTTPException(400, "Enter at least one ingredient.")
    response = {"matches": recipes.find_by_ingredients(names), "ai_recipe": None, "ai_error": None}
    try:
        recipe = ai_service.suggest_recipe(names, data.notes or "")
        started = time.time()
        recipe["nutrition"] = calculate(recipe["ingredients"], recipe["servings"])
        print(f"[AI] USDA nutrition for the AI recipe took {time.time() - started:.1f} s", flush=True)
        response["ai_recipe"] = recipe
    except ai_service.AIError as e:
        response["ai_error"] = str(e)
    return response


@app.post("/api/ai/save", status_code=201)
def ai_save(data: RecipeIn):
    return recipes.create_recipe(data.model_dump(), source="ai")


# ---------- status ----------

@app.get("/api/status")
def status():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    conn.close()
    return {
        "recipes": count,
        "ai_configured": ai_service.is_configured(),
        "ai_model": config.GEMINI_MODEL,
        "usda_key": "personal" if config.USDA_API_KEY != "DEMO_KEY" else "DEMO_KEY",
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
