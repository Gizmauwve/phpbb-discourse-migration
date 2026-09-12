#!/usr/bin/env bash
set -euo pipefail

echo "Installation des dépendances système..."
sudo apt-get update
sudo apt-get install -y libmariadb-dev build-essential pkg-config

echo "Installation des gems Ruby..."
bundle install