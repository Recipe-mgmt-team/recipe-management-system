@echo off
cd /d "%~dp0"
title Recipe Management System
if not exist .env (
  copy .env.example .env >nul
  echo .env created. Open it and add your USDA_API_KEY and GEMINI_API_KEY, then run this file again.
  notepad .env
  pause
  exit /b
)
echo Installing requirements...
pip install -q -r requirements.txt
if not exist recipes.db (
  echo First run: importing recipes from TheMealDB, this takes a few minutes...
  python import_recipes.py --limit 80
)
echo Starting server at http://127.0.0.1:8000
start "" http://127.0.0.1:8000
python main.py
pause
