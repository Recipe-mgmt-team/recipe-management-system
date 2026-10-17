import sqlite3
import os
import json

DB_FILE = os.path.join(os.path.dirname(__file__), "recipes.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_category(calories: float, carbs_g: float, protein_g: float, fat_g: float) -> str:
    """
    Besin değerlerine göre otomatik kategori belirleme mantığı.
    """
    if carbs_g <= 12 and fat_g >= 18:
        return "Keto Dostu"
    elif protein_g >= 28:
        return "Yüksek Protein"
    elif carbs_g <= 18:
        return "Düşük Karbonhidrat"
    elif calories <= 380:
        return "Düşük Kalori & Diyet"
    elif calories >= 750:
        return "Yüksek Enerji / Doyurucu"
    else:
        return "Dengeli Beslenme"

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        instructions TEXT NOT NULL,
        prep_time_min INTEGER DEFAULT 20,
        servings INTEGER DEFAULT 2,
        difficulty TEXT DEFAULT 'Orta',
        category TEXT NOT NULL,
        image_url TEXT,
        is_ai_generated INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount TEXT,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER UNIQUE NOT NULL,
        calories REAL NOT NULL,
        protein_g REAL NOT NULL,
        carbs_g REAL NOT NULL,
        fat_g REAL NOT NULL,
        fiber_g REAL DEFAULT 0.0,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    # Seed starter recipes if empty
    cursor.execute("SELECT COUNT(*) as count FROM recipes")
    if cursor.fetchone()["count"] == 0:
        seed_starter_recipes(cursor)
        conn.commit()

    conn.close()

def seed_starter_recipes(cursor):
    sample_recipes = [
        {
            "title": "Izgara Tavuklu Kinoa Kasesi",
            "description": "Yüksek proteinli, taze sebzeler ve zeytinyağlı limon sosu ile zenginleştirilmiş dengeli bir öğün.",
            "prep_time_min": 25,
            "servings": 2,
            "difficulty": "Kolay",
            "instructions": "1. Kinoayı 1.5 su bardağı suda 15 dakika haşlayın.\n2. Tavuk göğsünü zeytinyağı, kekik ve tuz ile marine edip ızgara tavada pişirin.\n3. Salatalık, kiraz domates ve avokadoyu küp doğrayın.\n4. Kaseye kinoayı taban yapıp üzerine dilimlenmiş tavuk ve sebzeleri yerleştirin.",
            "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80",
            "ingredients": [
                ("Tavuk Göğsü", "300 gr"),
                ("Kinoa", "1 su bardağı"),
                ("Kiraz Domates", "8 adet"),
                ("Avokado", "1/2 adet"),
                ("Zeytinyağı", "1 yemek kaşığı"),
                ("Limon", "1/2 adet")
            ],
            "nutrition": {"calories": 480, "protein_g": 42.0, "carbs_g": 38.0, "fat_g": 16.0, "fiber_g": 6.5}
        },
        {
            "title": "Fırında Sebzeli Somon & Kuşkonmaz",
            "description": "Omega-3 zengini somon fileto, fırınlanmış kuşkonmaz ve sarımsaklı zeytinyağı sosuyla keto dostu bir lezzet.",
            "prep_time_min": 20,
            "servings": 2,
            "difficulty": "Kolay",
            "instructions": "1. Fırını 200°C'ye ısıtın.\n2. Somon filetoları ve kuşkonmazları fırın tepsisine dizin.\n3. Üzerine zeytinyağı, sarımsak, tuz ve karabiber gezdirin.\n4. 15-18 dakika somonlar nar gibi kızarana kadar fırınlayın.",
            "image_url": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&auto=format&fit=crop&q=80",
            "ingredients": [
                ("Somon Fileto", "350 gr"),
                ("Kuşkonmaz", "1 demet"),
                ("Sarımsak", "2 diş"),
                ("Zeytinyağı", "2 yemek kaşığı"),
                ("Limon", "1 adet")
            ],
            "nutrition": {"calories": 420, "protein_g": 36.0, "carbs_g": 6.0, "fat_g": 28.0, "fiber_g": 3.0}
        },
        {
            "title": "Klasik Pratik Menemen",
            "description": "Taze domates, biber ve yumurtanın mükemmel uyumuyla geleneksel düşük karbonhidratlı lezzet.",
            "prep_time_min": 15,
            "servings": 2,
            "difficulty": "Kolay",
            "instructions": "1. Biberleri ince doğrayıp zeytinyağında hafifçe soteleyin.\n2. Kabukları soyulmuş küp domatesleri ekleyip suyunu çekene kadar pişirin.\n3. Çırpılmış yumurtaları ekleyip kısık ateşte hafif sulu kalacak şekilde karıştırın.",
            "image_url": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&auto=format&fit=crop&q=80",
            "ingredients": [
                ("Yumurta", "3 adet"),
                ("Domates", "3 adet"),
                ("Yeşil Biber", "3 adet"),
                ("Zeytinyağı", "1.5 yemek kaşığı"),
                ("Tuz & Pul Biber", "1 çay kaşığı")
            ],
            "nutrition": {"calories": 260, "protein_g": 16.0, "carbs_g": 10.0, "fat_g": 18.0, "fiber_g": 3.2}
        },
        {
            "title": "Zencefilli Kırmızı Mercimek Çorbası",
            "description": "Düşük kalorili, metabolizma hızlandıran zencefilli ve zerdeçallı detoks etkili çorba.",
            "prep_time_min": 30,
            "servings": 4,
            "difficulty": "Kolay",
            "instructions": "1. Soğan ve havucu zeytinyağında 3 dakika kavurun.\n2. Yıkanmış kırmızı mercimek, rendelenmiş taze zencefil ve zerdeçalı ekleyin.\n3. 5 su bardağı sıcak su ekleyip 20 dakika mercimekler yumuşayana kadar kaynatın.\n4. Blenderdan geçirip pürüzsüz servis edin.",
            "image_url": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&auto=format&fit=crop&q=80",
            "ingredients": [
                ("Kırmızı Mercimek", "1 su bardağı"),
                ("Soğan", "1 adet"),
                ("Havuç", "1 adet"),
                ("Taze Zencefil", "1 tatlı kaşığı"),
                ("Zerdeçal", "1 çay kaşığı"),
                ("Zeytinyağı", "1 yemek kaşığı")
            ],
            "nutrition": {"calories": 185, "protein_g": 11.0, "carbs_g": 26.0, "fat_g": 3.5, "fiber_g": 6.0}
        },
        {
            "title": "Kremalı Mantarlı İtalyan Penne",
            "description": "Taze kestane mantarı, fesleğen ve hafif krema sosu ile hazırlanan karbonhidrat ve enerji zengini makarna.",
            "prep_time_min": 20,
            "servings": 2,
            "difficulty": "Orta",
            "instructions": "1. Makarnayı tuzlu suda 'al dente' haşlayın.\n2. Mantarları dilimleyip tereyağında soteleyin, sarımsak ekleyin.\n3. Kremayı ilave edip 2 dakika kısık ateşte çektirin.\n4. Süzülen makarnayı sosla birleştirip taze fesleğenle servis edin.",
            "image_url": "https://images.unsplash.com/photo-1621996346565-e3d5d6281724?w=600&auto=format&fit=crop&q=80",
            "ingredients": [
                ("Penne Makarna", "200 gr"),
                ("Mantar", "250 gr"),
                ("Sarımsak", "2 diş"),
                ("Süt Kreması", "100 ml"),
                ("Tereyağı", "1 yemek kaşığı"),
                ("Fesleğen", "4 yaprak")
            ],
            "nutrition": {"calories": 560, "protein_g": 15.0, "carbs_g": 72.0, "fat_g": 24.0, "fiber_g": 4.5}
        }
    ]

    for item in sample_recipes:
        nutr = item["nutrition"]
        cat = calculate_category(nutr["calories"], nutr["carbs_g"], nutr["protein_g"], nutr["fat_g"])
        
        cursor.execute("""
            INSERT INTO recipes (title, description, instructions, prep_time_min, servings, difficulty, category, image_url, is_ai_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (item["title"], item["description"], item["instructions"], item["prep_time_min"], item["servings"], item["difficulty"], cat, item["image_url"]))
        
        recipe_id = cursor.lastrowid

        for ing_name, ing_amount in item["ingredients"]:
            cursor.execute("""
                INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)
            """, (recipe_id, ing_name, ing_amount))

        cursor.execute("""
            INSERT INTO nutrition (recipe_id, calories, protein_g, carbs_g, fat_g, fiber_g)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (recipe_id, nutr["calories"], nutr["protein_g"], nutr["carbs_g"], nutr["fat_g"], nutr.get("fiber_g", 0.0)))
