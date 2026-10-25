@echo off
rem Lance la page des annonces puis l'ouvre dans le navigateur.
cd /d "%~dp0"
start "" http://localhost:5000
py app.py
