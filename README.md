# Migration phpBB 3.0.x → Discourse

Guide complet et automatisé pour migrer un forum phpBB 3.0.x vers Discourse.

## 📋 Structure du projet

```
.
├── scripts/              # Scripts de migration
├── data/                 # Dossiers de données (export, conversion, logs)
├── tests/                # Tests de validation
├── docker-compose.yml    # Configuration Discourse local
├── CHECKLIST.md          # Recette de validation
└── README.md             # Cette documentation
```

## 🚀 Démarrage rapide

### Prérequis

- Python 3.8+
- Docker & Docker Compose (pour Discourse local)
- MySQL/MariaDB (accès à la base phpBB)
- ~20 GB d'espace disque (pour 8.69 GB de données)

### Installation

```bash
git clone https://github.com/Gizmauwve/phpbb-discourse-migration.git
cd phpbb-discourse-migration

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## 📊 Workflow de migration

### 1️⃣ Lancer Discourse localement

```bash
docker-compose up -d
# Accès : http://localhost:3000
```

### 2️⃣ Exporter les données phpBB

```bash
python scripts/export_phpbb.py --source ../Input --output ./data/export --verbose
```

**Options** :
- `--source` : Chemin du répertoire phpBB cloné (défaut: `../Input`)
- `--output` : Dossier de destination (défaut: `./data/export`)
- `--verbose` : Afficher les logs détaillés
- `--db-only` : Export base de données uniquement
- `--files-only` : Export pièces jointes uniquement

### 3️⃣ Convertir au format Discourse

```bash
python scripts/convert_data.py --input ./data/export --output ./data/converted --verbose
```

**Options** :
- `--input` : Dossier d'export phpBB
- `--output` : Dossier de destination
- `--mapping-file` : Fichier de mapping personnalisé (JSON)
- `--skip-files` : Ignorer les pièces jointes

### 4️⃣ Importer dans Discourse

```bash
python scripts/import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key YOUR_API_KEY --admin-email admin@example.com
```

**Options** :
- `--source` : Dossier des données converties
- `--target` : URL de Discourse (défaut: `http://localhost:3000`)
- `--api-key` : Clé API Discourse
- `--admin-email` : Email admin pour l'import
- `--batch-size` : Taille des lots (défaut: 100)
- `--dry-run` : Simulation sans import réel

### 5️⃣ Valider la migration

```bash
python scripts/validate_migration.py --phpbb ../Input --discourse http://localhost:3000 --verbose
```

**Options** :
- `--phpbb` : Chemin du forum phpBB
- `--discourse` : URL de Discourse
- `--output` : Fichier de rapport (défaut: `./data/logs/validation.html`)

## 📝 Recette de validation

Voir **CHECKLIST.md** pour la liste complète des tests de migration.

Utilise aussi :
```bash
python tests/test_migration.py
```

## 📂 Structure des données

### Export phpBB

```
data/export/
├── users.json          # Utilisateurs
├── categories.json     # Catégories/Forums
├── topics.json         # Sujets
├── posts.json          # Messages
├── attachments.json    # Métadonnées pièces jointes
└── files/              # Fichiers uploadés
    ├── avatars/
    ├── attachments/
    └── ...
```

### Données converties

```
data/converted/
├── users.ndjson       # Utilisateurs (Discourse format)
├── categories.ndjson  # Catégories
├── topics.ndjson      # Sujets
├── posts.ndjson       # Posts
└── files/             # Fichiers organisés
```

## 🔍 Logs et debugging

Les logs détaillés sont disponibles dans :

```
data/logs/
├── export_phpbb.log
├── convert_data.log
├── import_discourse.log
└── validation.log
```

Pour debugging avancé :
```bash
python scripts/export_phpbb.py --source ../Input --debug
```

## ⚠️ Points importants

1. **Backup** : Fais un backup complet avant de commencer
2. **Test d'abord** : Teste sur un petit sous-ensemble de données
3. **Validation** : Vérifie chaque étape avec la recette
4. **Pièces jointes** : Les fichiers volumineux peuvent prendre du temps
5. **Encodage** : Les vieilles versions phpBB peuvent avoir des problèmes d'encodage

## 🐛 Troubleshooting

### Erreur de connexion MySQL
```
FileNotFoundError: Config phpBB non trouvé
```
→ Vérifie que `--source` pointe vers le bon répertoire

### Erreur d'import Discourse
```
401 Unauthorized
```
→ Vérifie que l'API key est correcte et l'admin email valide

### Fichiers corrompus
→ Utilise `--skip-files` pour migrer les données sans pièces jointes

## 📞 Support

Pour les problèmes :
1. Vérifie les logs : `tail -f data/logs/*.log`
2. Lance la validation : `python scripts/validate_migration.py --verbose`
3. Crée une issue GitHub

## 📄 License

MIT

---

**Prêt ? Lance la migration ! 🚀**
