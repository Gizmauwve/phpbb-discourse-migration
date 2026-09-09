@echo off
title Discourse - environnement local

echo.
echo ========================================
echo       DEMARRAGE DE DISCOURSE
echo ========================================
echo.

echo [1/4] Demarrage de Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Attente de Docker...
:waitdocker
timeout /t 3 /nobreak >nul
docker version >nul 2>&1
if errorlevel 1 (
    echo Docker n'est pas encore pret...
    goto waitdocker
)

echo Docker est pret.
echo.

echo [2/4] Demarrage de WSL Ubuntu...
wsl -d Ubuntu -- echo "Ubuntu OK"

echo.
echo [3/4] Ouverture du projet Discourse dans VS Code...
wsl -d Ubuntu -- bash -c "cd /home/flore/discourse && code ."

echo.
echo [4/4] Environnement pret.
echo.
echo Dans VS Code :
echo   Ctrl+Shift+P
echo   Dev Containers: Reopen in Container
echo.
echo Puis lancer la tache :
echo   boot-dev
echo.
pause