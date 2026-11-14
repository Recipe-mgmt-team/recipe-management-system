@echo off
cd /d "%~dp0"
title Recalculate nutrition
echo Matching ingredients with USDA again and recalculating all recipes...
python import_recipes.py --recalculate --refresh-usda
echo.
echo Done. You can start the site with baslat.bat
pause
