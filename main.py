from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from database import get_db, init_db, calculate_category
from ai_service import ai_service

app = FastAPI(title="Recipe Management System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: Veritabanını başlat
@app.on_event("startup")
def startup_event():
    init_db()

# Pydantic Modelleri
class IngredientItem(BaseModel):
    name: str
    amount: Optional[str] = ""

class NutritionItem(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = 0.0

class RecipeCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    instructions: str
    prep_time_min: Optional[int] = 20
    servings: Optional[int] = 2
    difficulty: Optional[str] = "Orta"
    image_url: Optional[str] = None
    ingredients: List[IngredientItem]
    nutrition: NutritionItem

class AIGenerateRequest(BaseModel):
    ingredients: List[str]
    meal_type: Optional[str] = "Akşam Yemeği"
    dietary: Optional[str] = "Tümü"

class ApiKeyRequest(BaseModel):
    api_key: str

# API Rotaları

@app.get("/api/recipes")
def get_recipes(
    search: Optional[str] = None,
    ingredient: Optional[str] = None,
    category: Optional[str] = None,
    max_calories: Optional[float] = None
):
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT r.*, n.calories, n.protein_g, n.carbs_g, n.fat_g, n.fiber_g,
               GROUP_CONCAT(i.name, ', ') as ingredient_names
        FROM recipes r
        JOIN nutrition n ON r.id = n.recipe_id
        LEFT JOIN ingredients i ON r.id = i.recipe_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (r.title LIKE ? OR r.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if category and category != "Tümü":
        query += " AND r.category = ?"
        params.append(category)

    if max_calories:
        query += " AND n.calories <= ?"
        params.append(max_calories)

    query += " GROUP BY r.id"

    # Malzemeye göre arama (HAVING ile veya JOIN'de)
    if ingredient:
        query += " HAVING (r.id IN (SELECT recipe_id FROM ingredients WHERE name LIKE ?))"
        params.append(f"%{ingredient}%")

    query += " ORDER BY r.id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "prep_time_min": row["prep_time_min"],
            "servings": row["servings"],
            "difficulty": row["difficulty"],
            "category": row["category"],
            "image_url": row["image_url"],
            "is_ai_generated": bool(row["is_ai_generated"]),
            "created_at": row["created_at"],
            "nutrition": {
                "calories": row["calories"],
                "protein_g": row["protein_g"],
                "carbs_g": row["carbs_g"],
                "fat_g": row["fat_g"],
                "fiber_g": row["fiber_g"]
            },
            "ingredients_summary": row["ingredient_names"]
        })

    conn.close()
    return results

@app.get("/api/recipes/{recipe_id}")
def get_recipe_detail(recipe_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        conn.close()
        raise HTTPException(status_code=404, detail="Tarif bulunamadı.")

    cursor.execute("SELECT name, amount FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    ingredients = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT calories, protein_g, carbs_g, fat_g, fiber_g FROM nutrition WHERE recipe_id = ?", (recipe_id,))
    nutrition = cursor.fetchone()

    conn.close()
    return {
        **dict(recipe),
        "is_ai_generated": bool(recipe["is_ai_generated"]),
        "ingredients": ingredients,
        "nutrition": dict(nutrition) if nutrition else None
    }

@app.post("/api/recipes")
def create_recipe(data: RecipeCreate):
    conn = get_db()
    cursor = conn.cursor()

    # Besin değerlerinden kategori hesapla
    category = calculate_category(
        data.nutrition.calories,
        data.nutrition.carbs_g,
        data.nutrition.protein_g,
        data.nutrition.fat_g
    )

    image = data.image_url or "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=600&auto=format&fit=crop&q=80"

    cursor.execute("""
        INSERT INTO recipes (title, description, instructions, prep_time_min, servings, difficulty, category, image_url, is_ai_generated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (data.title, data.description, data.instructions, data.prep_time_min, data.servings, data.difficulty, category, image))
    
    recipe_id = cursor.lastrowid

    for ing in data.ingredients:
        cursor.execute("""
            INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)
        """, (recipe_id, ing.name, ing.amount))

    cursor.execute("""
        INSERT INTO nutrition (recipe_id, calories, protein_g, carbs_g, fat_g, fiber_g)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (recipe_id, data.nutrition.calories, data.nutrition.protein_g, data.nutrition.carbs_g, data.nutrition.fat_g, data.nutrition.fiber_g or 0.0))

    conn.commit()
    conn.close()
    return {"status": "success", "recipe_id": recipe_id, "category": category}

@app.post("/api/recipes/generate-ai")
def generate_ai_recipe(req: AIGenerateRequest):
    """
    LLM API entegrasyonu: Kullanıcının evdeki malzemelerinden yeni akıllı tarif ve besin hesabı üretir.
    """
    if not req.ingredients:
        raise HTTPException(status_code=400, detail="Lütfen en az 1 malzeme giriniz.")
    
    generated = ai_service.generate_recipe_from_ingredients(
        req.ingredients,
        meal_type=req.meal_type,
        dietary=req.dietary
    )
    return generated

@app.post("/api/recipes/save-ai")
def save_ai_recipe(data: dict):
    """
    LLM tarafından üretilen bir tarifi doğrudan veritabanına kaydeder.
    """
    conn = get_db()
    cursor = conn.cursor()

    nutr = data.get("nutrition", {})
    category = data.get("category") or calculate_category(
        float(nutr.get("calories", 400)),
        float(nutr.get("carbs_g", 30)),
        float(nutr.get("protein_g", 20)),
        float(nutr.get("fat_g", 15))
    )

    cursor.execute("""
        INSERT INTO recipes (title, description, instructions, prep_time_min, servings, difficulty, category, image_url, is_ai_generated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        data.get("title", "Akıllı Tarif"),
        data.get("description", ""),
        data.get("instructions", ""),
        data.get("prep_time_min", 20),
        data.get("servings", 2),
        data.get("difficulty", "Kolay"),
        category,
        data.get("image_url", "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=600&auto=format&fit=crop&q=80")
    ))
    
    recipe_id = cursor.lastrowid

    for ing in data.get("ingredients", []):
        cursor.execute("""
            INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)
        """, (recipe_id, ing.get("name", ""), ing.get("amount", "")))

    cursor.execute("""
        INSERT INTO nutrition (recipe_id, calories, protein_g, carbs_g, fat_g, fiber_g)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        recipe_id,
        float(nutr.get("calories", 0)),
        float(nutr.get("protein_g", 0)),
        float(nutr.get("carbs_g", 0)),
        float(nutr.get("fat_g", 0)),
        float(nutr.get("fiber_g", 0))
    ))

    conn.commit()
    conn.close()
    return {"status": "success", "recipe_id": recipe_id, "message": "Yapay zeka tarifi başarıyla kaydedildi!"}

@app.get("/api/categories")
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) as count FROM recipes GROUP BY category")
    rows = cursor.fetchall()
    conn.close()
    return [{"category": r["category"], "count": r["count"]} for r in rows]

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM recipes")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as ai_count FROM recipes WHERE is_ai_generated = 1")
    ai_count = cursor.fetchone()["ai_count"]

    cursor.execute("SELECT AVG(calories) as avg_cal, AVG(protein_g) as avg_protein FROM nutrition")
    averages = cursor.fetchone()

    conn.close()
    return {
        "total_recipes": total,
        "ai_recipes": ai_count,
        "avg_calories": round(averages["avg_cal"] or 0, 1),
        "avg_protein": round(averages["avg_protein"] or 0, 1),
        "has_gemini_key": bool(ai_service.api_key)
    }

@app.post("/api/settings/api-key")
def update_api_key(req: ApiKeyRequest):
    ai_service.set_api_key(req.api_key.strip())
    return {"status": "success", "has_key": bool(ai_service.api_key)}

# Frontend static dosyalarını sun
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
