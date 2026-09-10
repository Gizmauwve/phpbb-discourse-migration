@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Surfrepotes - environnement Discourse local

echo.
echo ================================================
echo     SURFREPOTES - ENVIRONNEMENT LOCAL
echo ================================================
echo.

REM ============================================================
REM CONFIGURATION
REM ============================================================

set "WSL_DISTRO=Ubuntu"
set "PROJECT=/home/flore/discourse"

set "SQL_SOURCE_WIN=C:\Users\flore\source\repos\Surfrepotes\Travail\Input\surfrepotes_mysql_db.sql"
set "SQL_SOURCE_WSL=/mnt/c/Users/flore/source/repos/Surfrepotes/Travail/Input/surfrepotes_mysql_db.sql"
set "SQL_LOCAL=/home/flore/discourse/surfrepotes_mysql_db.sql"
set "SQL_HASH_FILE=/home/flore/discourse/.surfrepotes_sql.sha256"

set "MARIADB_CONTAINER=phpbb-mariadb"
set "MARIADB_ROOT_PASSWORD=phpbbroot"
set "MARIADB_DATABASE=surfrepotes"

set "IMPORT_NETWORK=phpbb_import"
set "DISCOURSE_CONTAINER=epic_fermi"

REM ============================================================
REM 1 - DOCKER DESKTOP
REM ============================================================

echo [1/7] Demarrage de Docker Desktop...

start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Attente de Docker...

:WAIT_DOCKER
wsl -d %WSL_DISTRO% -- bash -lc "docker version >/dev/null 2>&1"
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto WAIT_DOCKER
)

echo Docker est pret.
echo.

REM ============================================================
REM 2 - VERIFICATION DU DUMP SOURCE
REM ============================================================

echo [2/7] Verification du dump SQL source...

if not exist "%SQL_SOURCE_WIN%" (
    echo.
    echo ERREUR : fichier SQL introuvable :
    echo %SQL_SOURCE_WIN%
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%A in ('wsl -d %WSL_DISTRO% -- bash -lc "sha256sum '%SQL_SOURCE_WSL%' | cut -d ' ' -f1"') do (
    set "SOURCE_HASH=%%A"
)

echo SHA-256 source :
echo !SOURCE_HASH!
echo.

REM ============================================================
REM 3 - MARIA DB
REM ============================================================

echo [3/7] Preparation de MariaDB...

docker inspect %MARIADB_CONTAINER% >nul 2>&1

if errorlevel 1 (
    echo Conteneur MariaDB absent.
    echo Creation du conteneur...

    docker run -d ^
        --name %MARIADB_CONTAINER% ^
        -e MARIADB_ROOT_PASSWORD=%MARIADB_ROOT_PASSWORD% ^
        -e MARIADB_DATABASE=%MARIADB_DATABASE% ^
        mariadb:10.11

    if errorlevel 1 (
        echo ERREUR lors de la creation de MariaDB.
        pause
        exit /b 1
    )
) else (
    echo Conteneur MariaDB deja existant.
)

docker start %MARIADB_CONTAINER% >nul 2>&1

echo Attente de MariaDB...

:WAIT_MARIADB
docker exec %MARIADB_CONTAINER% ^
    mariadb-admin ping ^
    -uroot ^
    -p%MARIADB_ROOT_PASSWORD% >nul 2>&1

if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto WAIT_MARIADB
)

echo MariaDB est pret.
echo.

REM ============================================================
REM 4 - IMPORT SQL SI NECESSAIRE
REM ============================================================

echo [4/7] Verification du dump deja importe...

set "TABLE_EXISTS=0"

for /f "delims=" %%A in ('docker exec %MARIADB_CONTAINER% mariadb -uroot -p%MARIADB_ROOT_PASSWORD% %MARIADB_DATABASE% -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='%MARIADB_DATABASE%' AND table_name='phpbb3_users';"') do (
    set "TABLE_EXISTS=%%A"
)

set "OLD_HASH="

if exist "%SQL_HASH_FILE%" (
    for /f "delims=" %%A in ('wsl -d %WSL_DISTRO% -- bash -lc "cat '%SQL_HASH_FILE%'"') do (
        set "OLD_HASH=%%A"
    )
)

echo Table phpbb3_users : !TABLE_EXISTS!
echo Ancien SHA-256     : !OLD_HASH!
echo.

if "!TABLE_EXISTS!"=="1" if "!OLD_HASH!"=="!SOURCE_HASH!" (
    echo Dump deja importe et inchange.
    echo Aucun nouvel import SQL.
    goto SQL_DONE
)

if "!TABLE_EXISTS!"=="1" if "!OLD_HASH!"=="" (
    echo Base phpBB deja presente.
    echo Initialisation du suivi SHA-256 sans reimport.
    goto SAVE_HASH
)

if "!TABLE_EXISTS!"=="1" (
    echo.
    echo ATTENTION : le fichier SQL a change.
    echo Reconstruction de la base MariaDB...

    docker exec %MARIADB_CONTAINER% mariadb ^
        -uroot ^
        -p%MARIADB_ROOT_PASSWORD% ^
        -e "DROP DATABASE IF EXISTS %MARIADB_DATABASE%; CREATE DATABASE %MARIADB_DATABASE%;"

    if errorlevel 1 (
        echo ERREUR lors de la reconstruction de la base.
        pause
        exit /b 1
    )
)

echo Copie du dump SQL vers WSL...

wsl -d %WSL_DISTRO% -- bash -lc "cp '%SQL_SOURCE_WSL%' '%SQL_LOCAL%'"

if errorlevel 1 (
    echo ERREUR lors de la copie du dump SQL.
    pause
    exit /b 1
)

echo Import du dump SQL dans MariaDB...
echo.

wsl -d %WSL_DISTRO% -- bash -lc "docker exec -i %MARIADB_CONTAINER% mariadb -uroot -p%MARIADB_ROOT_PASSWORD% %MARIADB_DATABASE% < '%SQL_LOCAL%'"

if errorlevel 1 (
    echo.
    echo ERREUR pendant l'import SQL.
    pause
    exit /b 1
)

echo.
echo Import SQL termine.

:SAVE_HASH
wsl -d %WSL_DISTRO% -- bash -lc "echo %SOURCE_HASH% > '%SQL_HASH_FILE%'"

:SQL_DONE
echo.
echo Base phpBB disponible dans MariaDB.
echo.

REM ============================================================
REM 5 - RESEAU DOCKER
REM ============================================================

echo [5/7] Preparation du reseau Docker...

docker network inspect %IMPORT_NETWORK% >nul 2>&1
if errorlevel 1 (
    echo Creation du reseau %IMPORT_NETWORK%...
    docker network create %IMPORT_NETWORK%
)

docker network connect %IMPORT_NETWORK% %MARIADB_CONTAINER% >nul 2>&1
echo MariaDB connectee au reseau %IMPORT_NETWORK%.
echo.

REM ============================================================
REM 6 - OUVERTURE DE VS CODE
REM ============================================================

echo [6/7] Ouverture du projet Discourse...

wsl -d %WSL_DISTRO% -- bash -lc "cd %PROJECT% && code ."

echo.
echo VS Code est ouvert.
echo.
echo Dans VS Code :
echo.
echo   1. Ctrl+Shift+P
echo   2. Dev Containers: Reopen in Container
echo   3. Attendre que le conteneur soit pret
echo   4. Ouvrir un terminal Dev Container
echo   5. Installer les dependances systeme :
echo.
echo      sudo apt-get update
echo      sudo apt-get install -y libmariadb-dev build-essential pkg-config
echo      bundle install
echo.
echo   6. Verifier le reseau avec :
echo.
echo      getent hosts phpbb-mariadb
echo.
echo   7. Lancer l'import :
echo.
echo      ./script/import_scripts/phpbb3/run-surfrepotes.sh
echo.
echo   ou directement :
echo.
echo      bundle exec ruby script/import_scripts/phpbb3.rb script/import_scripts/phpbb3/surfrepotes.yml
echo.
echo   8. Ouvrir :
echo.
echo      http://localhost:3000
echo.
echo ========================================================
echo.
echo IMPORTANT :
echo Le conteneur Discourse doit etre cree par VS Code avant
echo que nous puissions automatiquement le connecter au reseau.
echo.
echo Après création du Dev Container, lance dans WSL :
echo.
echo   docker network connect %IMPORT_NETWORK% %DISCOURSE_CONTAINER%
echo.
echo Si la commande dit que le conteneur est deja connecte, c'est OK.
echo.
pause

REM ============================================================
REM 7 - MESSAGE FINAL
REM ============================================================

echo.
echo [7/7] Resume :
echo.
echo   - Docker Desktop : OK
echo   - Dump SQL : OK
echo   - MariaDB : OK
echo   - Reseau : %IMPORT_NETWORK%
echo   - Discourse : %DISCOURSE_CONTAINER%
echo.
echo Lance ensuite l'import depuis le Dev Container.
echo.

pause
endlocal