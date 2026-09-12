#!/usr/bin/env bash
set -euo pipefail

YAML="script/import_scripts/phpbb3/surfrepotes.yml"
IMPORTER="script/import_scripts/phpbb3.rb"

if [[ ! -f "$YAML" ]]; then
  echo "Erreur: fichier YAML introuvable: $YAML"
  exit 1
fi

echo "Lancement de l'import phpBB -> Discourse..."
bundle exec ruby "$IMPORTER" "$YAML"