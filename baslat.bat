@echo off
cd /d "%~dp0"
title Recipe Management System - NutriChef
echo ========================================================
echo    NutriChef - Akilli Yemek Tarifi & Besin Yonetimi
echo ========================================================
echo.
echo Gerekli kutuphaneler kontrol ediliyor...
pip install -q -r requirements.txt
echo.
echo Sunucu baslatiliyor (http://127.0.0.1:8000)...
echo Tarayiciniz otomatik olarak acilacaktir.
echo.
start http://127.0.0.1:8000
python main.py
pause
