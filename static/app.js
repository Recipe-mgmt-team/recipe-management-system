// Recipe Management System - frontend (plain JavaScript, no framework)

const PAGE_SIZE = 24;
const state = { offset: 0, total: 0, search: "", category: "" };

const $ = (sel) => document.querySelector(sel);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = body.detail || `Request failed (HTTP ${res.status})`;
    if (Array.isArray(msg)) msg = msg.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ");
    throw new Error(msg);
  }
  return body;
}

const round = (n) => Math.round(Number(n) || 0);

// ---------- routing ----------

function route() {
  const hash = location.hash.replace("#", "") || "recipes";
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  document.querySelectorAll("[data-nav]").forEach((a) =>
    a.classList.toggle("active", hash === a.dataset.nav));

  const match = hash.match(/^recipe-(\d+)$/);
  if (match) {
    $("#view-detail").classList.remove("hidden");
    showDetail(Number(match[1]));
  } else if (hash === "add" || hash === "ai") {
    $(`#view-${hash}`).classList.remove("hidden");
  } else {
    $("#view-recipes").classList.remove("hidden");
  }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

// ---------- recipe list ----------

function cardHtml(r) {
  const img = r.image_url
    ? `<img src="${esc(r.image_url)}" alt="" loading="lazy">`
    : `<div class="noimg">No photo</div>`;
  const kcal = r.nutrition?.total_count ? `${round(r.nutrition.calories)} kcal per serving` : "Nutrition pending";
  const origin = [r.cuisine, r.meal_type].filter(Boolean).join(" ");
  return `<a class="card" href="#recipe-${r.id}">
      ${img}
      <h3>${esc(r.title)}</h3>
      <p class="meta">${esc(origin || "Own recipe")}</p>
      <p class="meta">${kcal}</p>
      <span class="tag" data-cat="${esc(r.category)}">${esc(r.category)}</span>
      ${r.source === "ai" ? '<span class="tag ai">AI suggestion</span>' : ""}
    </a>`;
}

async function loadRecipes(append = false) {
  if (!append) state.offset = 0;
  const params = new URLSearchParams({ limit: PAGE_SIZE, offset: state.offset });
  if (state.search) params.set("search", state.search);
  if (state.category) params.set("category", state.category);
  try {
    const data = await api(`/api/recipes?${params}`);
    state.total = data.total;
    const html = data.items.map(cardHtml).join("");
    $("#recipeGrid").innerHTML = append ? $("#recipeGrid").innerHTML + html : html;
    state.offset += data.items.length;
    $("#loadMoreBtn").classList.toggle("hidden", state.offset >= state.total);
    if (data.total === 0) {
      $("#listInfo").innerHTML = state.search || state.category
        ? "No recipes match this search."
        : 'No recipes yet. Run <code>python import_recipes.py</code> or <a href="#add">add one</a>.';
    } else {
      $("#listInfo").textContent = `${data.total} recipe${data.total === 1 ? "" : "s"}`;
    }
  } catch (e) {
    $("#listInfo").textContent = `Could not load recipes: ${e.message}`;
  }
}

async function loadCategories() {
  try {
    const cats = await api("/api/categories");
    $("#categorySelect").innerHTML = '<option value="">All categories</option>' +
      cats.map((c) => `<option value="${esc(c.category)}">${esc(c.category)} (${c.count})</option>`).join("");
    $("#categorySelect").value = state.category;
  } catch { /* the list still works without the filter */ }
}

let searchTimer;
$("#searchInput").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.search = e.target.value.trim(); loadRecipes(); }, 300);
});
$("#categorySelect").addEventListener("change", (e) => { state.category = e.target.value; loadRecipes(); });
$("#loadMoreBtn").addEventListener("click", () => loadRecipes(true));

// ---------- shared pieces ----------

function nutritionHtml(n, servings, estimated = false) {
  if (!n || !n.total_count) {
    return '<p class="warn">Nutrition could not be calculated yet (no ingredient matched USDA data).</p>';
  }
  const items = [
    ["calories", "kcal"], ["protein_g", "g protein"], ["carbs_g", "g carbs"], ["fat_g", "g fat"], ["fiber_g", "g fiber"],
  ];
  return `<div class="nutri">${items.map(([k, label]) =>
      `<div><div class="v">${round(n[k])}</div><div class="k">${label}</div></div>`).join("")}</div>
    <p class="muted" style="font-size:.85rem">Per serving (${servings} servings${estimated
      ? ", estimated from the total weight because the source does not state it" : ""}).
      ${n.matched_count} of ${n.total_count} measured ingredients matched in USDA FoodData Central.</p>`;
}

function ingredientTable(ings) {
  const rows = ings.map((i) => `<tr class="${i.fdc_id ? "" : "unmatched"}">
      <td>${esc(i.name)}${i.usda_description ? `<span class="src">USDA ${esc(i.fdc_id)}: ${esc(i.usda_description)}</span>`
        : '<span class="src">No USDA match</span>'}</td>
      <td>${esc(i.amount)}</td>
      <td class="num">${i.grams ? `${round(i.grams)} g` : "-"}</td>
      <td class="num">${i.fdc_id && i.grams ? round(i.calories) : "-"}</td>
    </tr>`).join("");
  return `<div class="table-wrap"><table>
      <thead><tr><th>Ingredient</th><th>Amount</th><th class="num">Weight</th><th class="num">kcal (total)</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
}

function stepsHtml(text) {
  const steps = String(text || "").split(/\n+/).map((s) => s.replace(/^\s*(step\s*)?\d+[.)]\s*/i, "").trim()).filter(Boolean);
  return `<ol class="steps">${steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`;
}

// ---------- detail ----------

async function showDetail(id) {
  const view = $("#view-detail");
  view.innerHTML = '<p class="muted">Loading...</p>';
  try {
    const r = await api(`/api/recipes/${id}`);
    const sourceText = { themealdb: "Imported from TheMealDB", ai: "Suggested by AI (Gemini)", user: "Added by a user" }[r.source];
    view.innerHTML = `
      <a class="back" href="#recipes">Back to recipes</a>
      <div class="detail-head">
        ${r.image_url ? `<img src="${esc(r.image_url)}" alt="${esc(r.title)}">` : '<div class="card"><div class="noimg">No photo</div></div>'}
        <div>
          <h1>${esc(r.title)}</h1>
          <p class="muted">${esc(r.description || "")}</p>
          <p class="meta">${esc(sourceText)}${r.prep_time_min ? `. ${r.prep_time_min} minutes` : ""}.</p>
          <span class="tag" data-cat="${esc(r.category)}">${esc(r.category)}</span>
          ${nutritionHtml(r.nutrition, r.servings, r.servings_estimated)}
          <div class="actions">
            <button class="btn btn-quiet" id="recalcBtn">Recalculate nutrition</button>
            <button class="btn btn-danger" id="deleteBtn">Delete recipe</button>
          </div>
          <p id="detailMsg" class="muted" role="status"></p>
        </div>
      </div>
      <h2>Ingredients</h2>
      ${ingredientTable(r.ingredients)}
      <h2>Method</h2>
      ${stepsHtml(r.instructions)}`;

    $("#recalcBtn").onclick = async () => {
      $("#detailMsg").textContent = "Recalculating...";
      try {
        const res = await api(`/api/recipes/${id}/recalculate`, { method: "POST" });
        await showDetail(id);
        if (res.warnings.length) $("#detailMsg").textContent = res.warnings.join(" ");
      } catch (e) { $("#detailMsg").textContent = e.message; }
    };
    $("#deleteBtn").onclick = async () => {
      if (!confirm(`Delete "${r.title}"? This cannot be undone.`)) return;
      await api(`/api/recipes/${id}`, { method: "DELETE" });
      location.hash = "recipes";
      loadRecipes(); loadCategories();
    };
  } catch (e) {
    view.innerHTML = `<a class="back" href="#recipes">Back to recipes</a><p class="error">${esc(e.message)}</p>`;
  }
}

// ---------- add recipe ----------

function addIngredientRow(name = "", amount = "") {
  const row = document.createElement("div");
  row.className = "ing-row";
  row.innerHTML = `
    <input aria-label="Ingredient name" placeholder="Ingredient, e.g. onion" value="${esc(name)}">
    <input aria-label="Amount" placeholder="Amount, e.g. 150 g" value="${esc(amount)}">
    <button type="button" class="btn btn-x" aria-label="Remove ingredient">&times;</button>`;
  row.querySelector("button").onclick = () => row.remove();
  $("#ingredientRows").appendChild(row);
}

function readForm() {
  const f = new FormData($("#addForm"));
  const ingredients = [...document.querySelectorAll("#ingredientRows .ing-row")].map((row) => {
    const [n, a] = row.querySelectorAll("input");
    return { name: n.value.trim(), amount: a.value.trim() };
  }).filter((i) => i.name);
  const num = (v) => (v === "" || v === null ? null : Number(v));
  return {
    title: f.get("title").trim(),
    description: f.get("description").trim(),
    servings: num(f.get("servings")) || 1,
    prep_time_min: num(f.get("prep_time_min")),
    meal_type: f.get("meal_type").trim(),
    image_url: f.get("image_url").trim() || null,
    instructions: f.get("instructions").trim(),
    ingredients,
  };
}

function showAddError(msg) {
  $("#addError").textContent = msg;
  $("#addError").classList.toggle("hidden", !msg);
}

$("#addIngredientBtn").onclick = () => addIngredientRow();

$("#previewBtn").onclick = async () => {
  const data = readForm();
  if (!data.ingredients.length) return showAddError("Add at least one ingredient first.");
  showAddError("");
  const box = $("#previewBox");
  box.classList.remove("hidden");
  box.innerHTML = '<p class="muted">Looking up ingredients in USDA FoodData Central...</p>';
  try {
    const res = await api("/api/nutrition/preview", {
      method: "POST", body: JSON.stringify({ servings: data.servings, ingredients: data.ingredients }),
    });
    box.innerHTML = `<div class="panel"><h3>Nutrition check</h3>
      ${nutritionHtml({ ...res.per_serving, matched_count: res.matched_count, total_count: res.total_count }, data.servings)}
      <p>Category: <span class="tag" data-cat="${esc(res.category)}">${esc(res.category)}</span></p>
      ${ingredientTable(res.ingredients)}
      ${res.warnings.map((w) => `<p class="warn">${esc(w)}</p>`).join("")}</div>`;
  } catch (e) { box.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
};

$("#addForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = readForm();
  if (data.title.length < 2) return showAddError("Give the recipe a title.");
  if (!data.ingredients.length) return showAddError("Add at least one ingredient.");
  if (data.instructions.length < 5) return showAddError("Write the instructions.");
  showAddError("");
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Saving...";
  try {
    const res = await api("/api/recipes", { method: "POST", body: JSON.stringify(data) });
    $("#addForm").reset(); $("#ingredientRows").innerHTML = ""; addIngredientRow(); addIngredientRow();
    $("#previewBox").classList.add("hidden");
    loadRecipes(); loadCategories();
    location.hash = `recipe-${res.id}`;
  } catch (err) { showAddError(err.message); }
  btn.disabled = false; btn.textContent = "Save recipe";
});

// ---------- AI suggestion ----------

let lastAiRecipe = null;

function aiRecipeHtml(r) {
  const n = r.nutrition;
  return `<div class="panel">
    <span class="tag ai">New idea from AI</span>
    <h3 style="margin-top:.5rem">${esc(r.title)}</h3>
    <p class="muted">${esc(r.description)}</p>
    ${nutritionHtml({ ...n.per_serving, matched_count: n.matched_count, total_count: n.total_count }, r.servings)}
    <p>Category: <span class="tag" data-cat="${esc(n.category)}">${esc(n.category)}</span></p>
    ${ingredientTable(n.ingredients)}
    ${stepsHtml(r.instructions)}
    <div class="actions"><button class="btn btn-primary" id="saveAiBtn">Save to recipes</button></div>
  </div>`;
}

$("#aiForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ingredients = $("#aiIngredients").value.split(",").map((s) => s.trim()).filter(Boolean);
  if (!ingredients.length) return;
  const body = JSON.stringify({ ingredients, notes: $("#aiNotes").value });
  const btn = $("#aiBtn"); btn.disabled = true;
  $("#aiResult").innerHTML = '<div id="aiBox"></div><h2>From the collection</h2><div id="matchBox"><p class="muted">Searching...</p></div>';

  // 1) stored recipes: fast, shown right away
  api("/api/ai/matches", { method: "POST", body }).then((matches) => {
    $("#matchBox").innerHTML = matches.length
      ? `<div class="grid">${matches.map(cardHtml).join("")}</div>`
      : '<p class="muted">No stored recipe uses these ingredients.</p>';
  }).catch((err) => { $("#matchBox").innerHTML = `<p class="error">${esc(err.message)}</p>`; });

  // 2) Gemini: can be slow, show a running timer and give up after 2 minutes
  const started = Date.now();
  const tick = () => { $("#aiStatus").textContent = `Asking Gemini... ${Math.round((Date.now() - started) / 1000)} s`; };
  tick();
  const timer = setInterval(tick, 1000);
  const controller = new AbortController();
  const abort = setTimeout(() => controller.abort(), 180000);
  try {
    const res = await api("/api/ai/suggest", { method: "POST", body, signal: controller.signal });
    if (res.ai_recipe) {
      lastAiRecipe = res.ai_recipe;
      $("#aiBox").innerHTML = aiRecipeHtml(res.ai_recipe);
      $("#aiStatus").textContent = `Done in ${Math.round((Date.now() - started) / 1000)} s.`;
      $("#saveAiBtn").onclick = async () => {
        const saveBtn = $("#saveAiBtn"); saveBtn.disabled = true;
        const r = lastAiRecipe;
        try {
          const saved = await api("/api/ai/save", { method: "POST", body: JSON.stringify({
            title: r.title, description: r.description, instructions: r.instructions, servings: r.servings,
            prep_time_min: r.prep_time_min, ingredients: r.ingredients,
          }) });
          loadRecipes(); loadCategories();
          location.hash = `recipe-${saved.id}`;
        } catch (err) { saveBtn.disabled = false; $("#aiStatus").textContent = err.message; }
      };
    } else {
      $("#aiStatus").textContent = "";
      $("#aiBox").innerHTML = `<p class="warn">${esc(res.ai_error)}</p>`;
    }
  } catch (err) {
    $("#aiStatus").textContent = "";
    $("#aiBox").innerHTML = `<p class="warn">${err.name === "AbortError"
      ? "No answer from Gemini after 3 minutes. Please try again." : esc(err.message)}</p>`;
  }
  clearInterval(timer); clearTimeout(abort);
  btn.disabled = false;
});

// ---------- start ----------

async function loadStatus() {
  try {
    const s = await api("/api/status");
    $("#statusLine").textContent = s.ai_configured ? `AI model: ${s.ai_model}` : "AI not set up (no GEMINI_API_KEY)";
  } catch { /* footer only */ }
}

addIngredientRow(); addIngredientRow();
loadRecipes(); loadCategories(); loadStatus();
route();
