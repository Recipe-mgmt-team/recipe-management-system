"""Test the Gemini connection and show which models your key can use.

    python check_gemini.py
"""
import time

import requests

from app import config

BASE = "https://generativelanguage.googleapis.com/v1beta"


def main():
    if len(config.GEMINI_API_KEY) < 10:
        print("GEMINI_API_KEY is empty. Put your key in the .env file.")
        return
    headers = {"x-goog-api-key": config.GEMINI_API_KEY}

    print("1) Models your key can use for text generation:")
    try:
        r = requests.get(f"{BASE}/models", headers=headers, params={"pageSize": 200}, timeout=20)
    except requests.RequestException as e:
        print("   Could not reach Google:", e)
        return
    if r.status_code != 200:
        print(f"   HTTP {r.status_code}: {r.text[:300]}")
        return
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    flash = [n for n in names if "flash" in n]
    for n in flash or names:
        print("   ", n)

    print(f"\n2) Speed test with GEMINI_MODEL = {config.GEMINI_MODEL}")
    for thinking in ([config.GEMINI_THINKING] if config.GEMINI_THINKING else []) + [None]:
        cfg = {"maxOutputTokens": 256}
        if thinking:
            cfg["thinkingConfig"] = {"thinkingLevel": thinking}
        label = f"thinking={thinking}" if thinking else "model default"
        start = time.time()
        try:
            r = requests.post(f"{BASE}/models/{config.GEMINI_MODEL}:generateContent", headers=headers,
                              json={"contents": [{"parts": [{"text": "Name one soup. One word."}]}],
                                    "generationConfig": cfg}, timeout=120)
            msg = r.json().get("error", {}).get("message", "") if r.status_code != 200 else "OK"
            print(f"   {label}: HTTP {r.status_code} in {time.time() - start:.1f} s  {msg[:150]}")
        except requests.RequestException as e:
            print(f"   {label}: failed after {time.time() - start:.1f} s ({e})")

    print("\nIf the main model is slow or fails, copy a faster name from list 1 into .env as GEMINI_MODEL")
    print("(a name with 'lite' in it is usually the fastest), then restart baslat.bat.")


if __name__ == "__main__":
    main()
