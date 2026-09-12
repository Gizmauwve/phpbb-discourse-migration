@echo off
title LM Studio Stack (Caddy + Cloudflared)

echo ==============================
echo  STOP anciens processus
echo ==============================

taskkill /IM caddy.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1

echo.
echo ==============================
echo  Lancement Caddy
echo ==============================

start "" caddy.exe run --config Caddyfile

timeout /t 2 >nul

echo.
echo ==============================
echo  Lancement Cloudflared
echo ==============================

start "" cloudflared tunnel --url http://127.0.0.1:8080

echo.
echo ==============================
echo  STACK ACTIF
echo ==============================
echo - Caddy : http://127.0.0.1:8080
echo - LM Studio : http://127.0.0.1:1234
echo - Tunnel : en cours...
echo.

pause