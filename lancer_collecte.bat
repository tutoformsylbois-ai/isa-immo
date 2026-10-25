@echo off
rem Collecte les nouvelles annonces (à planifier une fois par jour).
cd /d "%~dp0"
py collecte.py >> data\collecte.log 2>&1
