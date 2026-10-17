// State
let selectedIngredients = ["Tavuk", "Domates", "Biber"];
let currentAiRecipe = null;
let currentCategory = "Tümü";

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    renderSelectedTags();
    loadStats();
    loadRecipes();
    setupEventListeners();
}

function setupEventListeners() {
    // AI Şef Aç/Kapat
    const aiChefSection = document.getElementById("aiChefSection");
    document.getElementById("openAiChefBtn").addEventListener("click", () => {
        aiChefSection.classList.remove("hidden");
        aiChefSection.scrollIntoView({ behavior: "smooth" });
    });
    document.getElementById("closeAiChefBtn").addEventListener("click", () => {
        aiChefSection.classList.add("hidden");
    });

    // Hızlı Malzeme Ekleme Butonları
    const quickPills = document.querySelectorAll("#quickIngredientPills .pill-btn");
    quickPills.forEach(pill => {
        pill.addEventListener("click", () => {
            const ing = pill.getAttribute("data-ing");
            if (!selectedIngredients.includes(ing)) {
                selectedIngredients.push(ing);
                renderSelectedTags();
            }
        });
    });

    // Custom Malzeme Girişi (Enter Tuşu)
    const customInput = document.getElementById("customIngredientInput");
    customInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            const val = customInput.value.trim();
            if (val && !selectedIngredients.includes(val)) {
                selectedIngredients.push(val);
                renderSelectedTags();
                customInput.value = "";
            }
        }
    });

    // AI Tarif Üret Butonu
    document.getElementById("generateAiRecipeBtn").addEventListener("click", handleGenerateAiRecipe);

    // AI Tarifini Kaydet Butonu
    document.getElementById("saveAiRecipeBtn").addEventListener("click", handleSaveAiRecipe);

    // Arama Girdileri
    let searchTimeout;
    document.getElementById("recipeSearchInput").addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadRecipes, 300);
    });
    document.getElementById("ingredientSearchInput").addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadRecipes, 300);
    });

    // Kategori Filtre Butonları
    const catPills = document.querySelectorAll("#categoryFilters .filter-pill");
    catPills.forEach(btn => {
        btn.addEventListener("click", () => {
            catPills.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentCategory = btn.getAttribute("data-category");
            loadRecipes();
        });
    });

    // Yeni Tarif Ekle Modalı
    const addModal = document.getElementById("addRecipeModal");
    document.getElementById("openAddRecipeBtn").addEventListener("click", () => {
        addModal.classList.remove("hidden");
    });
    document.getElementById("closeAddModalBtn").addEventListener("click", () => {
        addModal.classList.add("hidden");
    });
    document.getElementById("cancelAddModalBtn").addEventListener("click", () => {
        addModal.classList.add("hidden");
    });
    document.getElementById("formAddIngRowBtn").addEventListener("click", addIngredientFormRow);
    document.getElementById("addRecipeForm").addEventListener("submit", handleAddRecipeSubmit);

    // Tarif Detay Modalı Kapatma
    const detailModal = document.getElementById("recipeDetailModal");
    document.getElementById("closeDetailModalBtn").addEventListener("click", () => {
        detailModal.classList.add("hidden");
    });

    // Ayarlar Modalı
    const settingsModal = document.getElementById("settingsModal");
    document.getElementById("openSettingsBtn").addEventListener("click", () => {
        settingsModal.classList.remove("hidden");
        checkApiKeyStatus();
    });
    document.getElementById("closeSettingsModalBtn").addEventListener("click", () => {
        settingsModal.classList.add("hidden");
    });
    document.getElementById("saveApiKeyBtn").addEventListener("click", handleSaveApiKey);
}

// Seçilen Tagleri Render Et
function renderSelectedTags() {
    const box = document.getElementById("selectedTagsBox");
    const input = document.getElementById("customIngredientInput");
    
    // Eski tagleri temizle (input hariç)
    const existingTags = box.querySelectorAll(".ing-tag");
    existingTags.forEach(t => t.remove());

    selectedIngredients.forEach(ing => {
        const tag = document.createElement("span");
        tag.className = "ing-tag";
        tag.innerHTML = `${ing} <i class="fa-solid fa-xmark"></i>`;
        tag.querySelector("i").addEventListener("click", () => {
            selectedIngredients = selectedIngredients.filter(i => i !== ing);
            renderSelectedTags();
        });
        box.insertBefore(tag, input);
    });
}

// İstatistikleri Yükle
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        document.getElementById("statTotalRecipes").textContent = data.total_recipes;
        document.getElementById("statAiRecipes").textContent = data.ai_recipes;
        document.getElementById("statAvgProtein").textContent = `${data.avg_protein}g`;
    } catch (err) {
        console.error("Stats yüklenirken hata:", err);
    }
}

// Tarifleri Yükle
async function loadRecipes() {
    const search = document.getElementById("recipeSearchInput").value.trim();
    const ingSearch = document.getElementById("ingredientSearchInput").value.trim();

    let url = `/api/recipes?category=${encodeURIComponent(currentCategory)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (ingSearch) url += `&ingredient=${encodeURIComponent(ingSearch)}`;

    try {
        const res = await fetch(url);
        const recipes = await res.json();
        renderRecipesGrid(recipes);
    } catch (err) {
        console.error("Tarifler yüklenirken hata:", err);
    }
}

// Izgaraya Kartları Bas
function renderRecipesGrid(recipes) {
    const grid = document.getElementById("recipesGrid");
    const emptyState = document.getElementById("emptyState");
    grid.innerHTML = "";

    if (!recipes || recipes.length === 0) {
        emptyState.classList.remove("hidden");
        return;
    }
    emptyState.classList.add("hidden");

    recipes.forEach(r => {
        const nutr = r.nutrition || {};
        const cal = Math.round(nutr.calories || 0);
        const protein = nutr.protein_g || 0;
        const carbs = nutr.carbs_g || 0;
        const fat = nutr.fat_g || 0;

        // Yüzdesel makro barları
        const totalMacros = (protein + carbs + fat) || 1;
        const pPercent = Math.round((protein / totalMacros) * 100);
        const cPercent = Math.round((carbs / totalMacros) * 100);
        const fPercent = Math.round((fat / totalMacros) * 100);

        const card = document.createElement("div");
        card.className = "recipe-card";
        card.innerHTML = `
            <div class="card-image-wrap">
                <img src="${r.image_url || 'https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=600'}" alt="${r.title}">
                <div class="card-floating-badge">${r.category}</div>
                <div class="card-floating-time"><i class="fa-regular fa-clock"></i> ${r.prep_time_min} dk</div>
            </div>
            <div class="card-body">
                <h3 class="card-title">${r.title}</h3>
                <p class="card-desc">${r.description || 'Nefis ve pratik ev yemeği.'}</p>
                
                <div class="card-nutri-summary">
                    <div class="nutri-top-row">
                        <span class="cal-pill">${cal} kcal</span>
                        <span class="macros-text">P: ${protein}g | K: ${carbs}g | Y: ${fat}g</span>
                    </div>
                    <div class="macro-progress-bar" title="Protein: %${pPercent}, Karb: %${cPercent}, Yağ: %${fPercent}">
                        <div class="bar-protein" style="width: ${pPercent}%"></div>
                        <div class="bar-carbs" style="width: ${cPercent}%"></div>
                        <div class="bar-fat" style="width: ${fPercent}%"></div>
                    </div>
                </div>
            </div>
        `;

        card.addEventListener("click", () => openRecipeDetail(r.id));
        grid.appendChild(card);
    });
}

// Tarif Detay Modalı Aç
async function openRecipeDetail(id) {
    try {
        const res = await fetch(`/api/recipes/${id}`);
        const r = await res.json();
        const modal = document.getElementById("recipeDetailModal");
        const header = document.getElementById("modalRecipeHeader");
        const body = document.getElementById("modalRecipeBody");

        header.innerHTML = `
            <div class="detail-header-info">
                <div class="badge-row">
                    <span class="badge badge-category">${r.category}</span>
                    ${r.is_ai_generated ? '<span class="badge badge-ai"><i class="fa-solid fa-brain"></i> AI Üretimi</span>' : ''}
                    <span class="badge badge-time"><i class="fa-regular fa-clock"></i> ${r.prep_time_min} dk</span>
                    <span class="badge badge-time"><i class="fa-solid fa-users"></i> ${r.servings} Porsiyon</span>
                </div>
                <h2>${r.title}</h2>
                <p>${r.description || ''}</p>
            </div>
        `;

        const nutr = r.nutrition || {};
        const ingsHtml = r.ingredients.map(ing => `
            <li><label><input type="checkbox"> <strong>${ing.name}</strong> - ${ing.amount || 'göz kararı'}</label></li>
        `).join("");

        body.innerHTML = `
            <!-- Besin Değerleri Detay Şeridi -->
            <div class="nutrition-strip">
                <div class="nutri-box">
                    <span class="n-val">${Math.round(nutr.calories || 0)}</span>
                    <span class="n-unit">kcal</span>
                    <span class="n-lbl">Kalori</span>
                </div>
                <div class="nutri-box">
                    <span class="n-val">${nutr.protein_g}g</span>
                    <span class="n-lbl">Protein</span>
                </div>
                <div class="nutri-box">
                    <span class="n-val">${nutr.carbs_g}g</span>
                    <span class="n-lbl">Karbonhidrat</span>
                </div>
                <div class="nutri-box">
                    <span class="n-val">${nutr.fat_g}g</span>
                    <span class="n-lbl">Sağlıklı Yağ</span>
                </div>
            </div>

            <div class="recipe-two-col">
                <div class="col-box">
                    <h4><i class="fa-solid fa-basket-shopping"></i> Malzemeler (${r.ingredients.length} adet):</h4>
                    <ul class="detail-ingredients-checklist">${ingsHtml}</ul>
                </div>
                <div class="col-box">
                    <h4><i class="fa-solid fa-fire-burner"></i> Hazırlanışı:</h4>
                    <div class="instructions-text">${r.instructions}</div>
                </div>
            </div>
        `;

        modal.classList.remove("hidden");
    } catch (err) {
        showToast("Tarif detayı alınamadı", "error");
    }
}

// AI Tarif Üretme İşlemi
async function handleGenerateAiRecipe() {
    if (selectedIngredients.length === 0) {
        showToast("Lütfen en az 1 malzeme seçin veya yazın!", "error");
        return;
    }

    const mealType = document.getElementById("aiMealTypeSelect").value;
    const dietary = document.getElementById("aiDietarySelect").value;
    const loading = document.getElementById("aiLoadingIndicator");
    const resultBox = document.getElementById("aiResultCard");
    const generateBtn = document.getElementById("generateAiRecipeBtn");

    loading.classList.remove("hidden");
    resultBox.classList.add("hidden");
    generateBtn.disabled = true;

    try {
        const res = await fetch("/api/recipes/generate-ai", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ingredients: selectedIngredients,
                meal_type: mealType,
                dietary: dietary
            })
        });

        if (!res.ok) throw new Error("Tarif üretilemedi.");
        const data = await res.json();
        currentAiRecipe = data;

        // Sonuçları Doldur
        document.getElementById("aiResultTitle").textContent = data.title;
        document.getElementById("aiResultDesc").textContent = data.description;
        document.getElementById("aiResultCategory").textContent = data.category;
        document.getElementById("aiResultTime").innerHTML = `<i class="fa-regular fa-clock"></i> ${data.prep_time_min} dk`;

        const nutr = data.nutrition || {};
        document.getElementById("aiNutrCal").textContent = Math.round(nutr.calories || 0);
        document.getElementById("aiNutrProtein").textContent = `${nutr.protein_g}g`;
        document.getElementById("aiNutrCarbs").textContent = `${nutr.carbs_g}g`;
        document.getElementById("aiNutrFat").textContent = `${nutr.fat_g}g`;

        const ingList = document.getElementById("aiResultIngredientsList");
        ingList.innerHTML = (data.ingredients || []).map(i => `<li><strong>${i.name}</strong> (${i.amount})</li>`).join("");

        document.getElementById("aiResultInstructions").textContent = data.instructions;

        loading.classList.add("hidden");
        resultBox.classList.remove("hidden");
        resultBox.scrollIntoView({ behavior: "smooth" });
        showToast("Akıllı tarif başarıyla oluşturuldu! ✨");
    } catch (err) {
        loading.classList.add("hidden");
        showToast("Tarif üretilirken bir hata oluştu: " + err.message, "error");
    } finally {
        generateBtn.disabled = false;
    }
}

// AI Tarifini Kaydet
async function handleSaveAiRecipe() {
    if (!currentAiRecipe) return;

    try {
        const res = await fetch("/api/recipes/save-ai", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(currentAiRecipe)
        });

        if (!res.ok) throw new Error("Kayıt başarısız.");
        showToast("Tarif başarıyla kaydedildi ve kataloğa eklendi! 🎉");
        loadRecipes();
        loadStats();
    } catch (err) {
        showToast("Kaydedilirken hata oluştu: " + err.message, "error");
    }
}

// Form Malzeme Satırı Ekle
function addIngredientFormRow() {
    const container = document.getElementById("formIngredientsContainer");
    const row = document.createElement("div");
    row.className = "ing-input-row";
    row.innerHTML = `
        <input type="text" placeholder="Malzeme Adı (örn: Zeytinyağı)" class="form-ing-name" required>
        <input type="text" placeholder="Miktar (örn: 2 yemek kaşığı)" class="form-ing-amount">
        <button type="button" class="delete-ing-btn"><i class="fa-solid fa-trash-can"></i></button>
    `;
    row.querySelector(".delete-ing-btn").addEventListener("click", () => row.remove());
    container.appendChild(row);
}

// Manuel Tarif Ekleme Submit
async function handleAddRecipeSubmit(e) {
    e.preventDefault();

    const title = document.getElementById("formTitle").value.trim();
    const description = document.getElementById("formDescription").value.trim();
    const prep_time_min = parseInt(document.getElementById("formPrepTime").value) || 20;
    const servings = parseInt(document.getElementById("formServings").value) || 2;
    const difficulty = document.getElementById("formDifficulty").value;
    const instructions = document.getElementById("formInstructions").value.trim();

    // Malzemeler
    const ingRows = document.querySelectorAll("#formIngredientsContainer .ing-input-row");
    const ingredients = [];
    ingRows.forEach(r => {
        const name = r.querySelector(".form-ing-name").value.trim();
        const amount = r.querySelector(".form-ing-amount").value.trim();
        if (name) ingredients.push({ name, amount });
    });

    // Besin Değerleri
    const calories = parseFloat(document.getElementById("formCal").value) || 0;
    const protein_g = parseFloat(document.getElementById("formProtein").value) || 0;
    const carbs_g = parseFloat(document.getElementById("formCarbs").value) || 0;
    const fat_g = parseFloat(document.getElementById("formFat").value) || 0;

    const payload = {
        title,
        description,
        prep_time_min,
        servings,
        difficulty,
        instructions,
        ingredients,
        nutrition: { calories, protein_g, carbs_g, fat_g, fiber_g: 0 }
    };

    try {
        const res = await fetch("/api/recipes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Tarif kaydedilemedi.");
        const result = await res.json();
        
        showToast(`Tarif kaydedildi! Otomatik Kategori: ${result.category}`);
        document.getElementById("addRecipeModal").classList.add("hidden");
        document.getElementById("addRecipeForm").reset();
        loadRecipes();
        loadStats();
    } catch (err) {
        showToast("Hata: " + err.message, "error");
    }
}

// API Anahtarı Durumu
async function checkApiKeyStatus() {
    const statusBox = document.getElementById("settingsKeyStatus");
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        if (data.has_gemini_key) {
            statusBox.innerHTML = '<span style="color: #34d399;"><i class="fa-solid fa-circle-check"></i> Aktif Google Gemini API Anahtarı Tanımlı.</span>';
        } else {
            statusBox.innerHTML = '<span style="color: #fbbf24;"><i class="fa-solid fa-circle-info"></i> API Anahtarı henüz girilmedi (Akıllı yerel simülatör devrede).</span>';
        }
    } catch (err) {
        statusBox.textContent = "Bağlantı hatası.";
    }
}

// API Anahtarı Kaydet
async function handleSaveApiKey() {
    const key = document.getElementById("geminiApiKeyInput").value.trim();
    if (!key) {
        showToast("Lütfen geçerli bir anahtar girin.", "error");
        return;
    }

    try {
        const res = await fetch("/api/settings/api-key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: key })
        });
        const data = await res.json();
        showToast("Gemini API Anahtarı başarıyla kaydedildi! 🤖");
        document.getElementById("settingsModal").classList.add("hidden");
    } catch (err) {
        showToast("Kaydedilemedi: " + err.message, "error");
    }
}

// Toast Bildirimi Göster
function showToast(message, type = "success") {
    const toast = document.getElementById("toastNotification");
    toast.textContent = message;
    toast.style.background = type === "error" ? "#ef4444" : "#10b981";
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3500);
}
