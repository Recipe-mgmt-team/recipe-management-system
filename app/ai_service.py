"""Recipe suggestions from Google Gemini.

Why the old version failed: it called "gemini-1.5-flash", which Google has
retired, so every request returned 404 and the code silently fell back to
random fake recipes. Now the model name is configurable (GEMINI_MODEL in .env),
errors are shown to the user, and nothing is made up when the call fails.

The model only writes the recipe (title, ingredients with metric amounts,
steps). Nutrition is calculated afterwards by our own code from USDA data.
"""
import json
import time

import requests

from app import config

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You are a home cook helping someone use what is in their kitchen.
Available ingredients: {ingredients}
Extra wishes from the user: {notes}

Write ONE practical recipe in English that uses mainly these ingredients.
You may add common pantry items (salt, pepper, oil, water, basic spices).

Rules for the ingredient list:
- "name" is a plain, generic food name (e.g. "onion", "chicken breast", "olive oil"), no brands.
- "amount" uses metric units when possible: grams (g) or millilitres (ml), or a count for whole
  items (e.g. "2" eggs). Use "to taste" only for salt and pepper.
- Do NOT include calories or nutrition values; they are calculated separately.

Reply with JSON only, in this shape:
{{"title": "...", "description": "one sentence", "servings": 2, "prep_time_min": 25,
  "ingredients": [{{"name": "...", "amount": "..."}}],
  "instructions": "1. ...\\n2. ...\\n3. ..."}}
"""


class AIError(Exception):
    pass


def is_configured() -> bool:
    return len(config.GEMINI_API_KEY.strip()) > 10


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIError("The AI answer did not contain a recipe.")
    return json.loads(text[start:end + 1])


def _validate(recipe: dict) -> dict:
    if not recipe.get("title") or not recipe.get("ingredients") or not recipe.get("instructions"):
        raise AIError("The AI answer was missing a title, ingredients or instructions.")
    ings = []
    for item in recipe["ingredients"]:
        if isinstance(item, dict) and item.get("name"):
            ings.append({"name": str(item["name"]).strip(), "amount": str(item.get("amount", "")).strip()})
        elif isinstance(item, str):
            ings.append({"name": item.strip(), "amount": ""})
    steps = recipe["instructions"]
    if isinstance(steps, list):
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return {
        "title": str(recipe["title"]).strip(),
        "description": str(recipe.get("description", "")).strip(),
        "servings": max(int(recipe.get("servings") or 2), 1),
        "prep_time_min": int(recipe.get("prep_time_min") or 0) or None,
        "ingredients": ings,
        "instructions": str(steps).strip(),
    }


def suggest_recipe(ingredients: list, notes: str = "") -> dict:
    if not is_configured():
        raise AIError("AI is not set up yet: add GEMINI_API_KEY to the .env file and restart the server.")
    prompt = PROMPT.format(ingredients=", ".join(ingredients), notes=notes.strip() or "none")
    models = [config.GEMINI_MODEL] + ([config.GEMINI_FALLBACK_MODEL] if config.GEMINI_FALLBACK_MODEL else [])
    resp = None
    started = time.time()
    use_thinking = bool(config.GEMINI_THINKING)
    for model in models:
        attempt = 0
        while attempt < 2:
            gen_config = {"temperature": 0.7, "responseMimeType": "application/json", "maxOutputTokens": 4096}
            if use_thinking:
                gen_config["thinkingConfig"] = {"thinkingLevel": config.GEMINI_THINKING}
            try:
                resp = requests.post(
                    API_URL.format(model=model),
                    headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                          "generationConfig": gen_config},
                    timeout=config.GEMINI_TIMEOUT,
                )
            except requests.Timeout as e:
                print(f"[AI] {model}: no answer after {time.time() - started:.1f} s", flush=True)
                raise AIError(f"Gemini did not answer within {config.GEMINI_TIMEOUT} seconds. "
                              "Run kontrol_et.bat to test the connection and see which models are fast.") from e
            except requests.RequestException as e:
                raise AIError(f"Could not reach the Gemini API: {e}") from e
            print(f"[AI] {model}: HTTP {resp.status_code} after {time.time() - started:.1f} s", flush=True)
            # Some models do not accept the thinking setting: ask again without it.
            if resp.status_code == 400 and use_thinking and "think" in resp.text.lower():
                print("[AI] model does not accept thinkingLevel, retrying without it", flush=True)
                use_thinking = False
                continue
            if resp.status_code not in (429, 500, 503):
                break
            attempt += 1
            time.sleep(2 * attempt)
        if resp.status_code == 200:
            break

    if resp.status_code != 200:
        try:
            message = resp.json().get("error", {}).get("message", "")
        except ValueError:
            message = resp.text[:200]
        hints = {
            400: "Check that GEMINI_API_KEY is correct.",
            403: "The API key is not allowed to use this model.",
            404: f"Model '{config.GEMINI_MODEL}' was not found. Set another GEMINI_MODEL in .env.",
            429: "Free quota used up for now. Wait a minute and try again.",
            503: "Gemini is busy right now. Try again in a few minutes.",
        }
        raise AIError(f"Gemini returned HTTP {resp.status_code}. {hints.get(resp.status_code, '')} {message}".strip())

    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if data["candidates"][0].get("finishReason") == "MAX_TOKENS":
            raise AIError("The AI answer was cut off. Please try again.")
        return _validate(_extract_json(text))
    except (KeyError, IndexError, ValueError, TypeError) as e:
        raise AIError("Could not read the AI answer. Please try again.") from e
