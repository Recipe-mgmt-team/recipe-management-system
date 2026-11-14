#!/usr/bin/env sh
cd "$(dirname "$0")"
[ -f .env ] || { cp .env.example .env; echo ".env created - add your API keys to it and run again."; exit 0; }
pip install -q -r requirements.txt
[ -f recipes.db ] || python3 import_recipes.py --limit 80
python3 main.py
