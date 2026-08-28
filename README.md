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

### Orchestration et monitoring

Le pipeline peut être lancé depuis un seul script. Le paramètre `--clone-path` doit désigner le chemin complet choisi lors de la récupération FTP, jusqu’au dossier qui contient `www`.

```powershell
python scripts/orchestrate_migration.py `
    --clone-path 'C:\chemin\choisi\Clone_2026' `
    --php 'C:\xampp\php\php.exe' `
    --base-url 'http://surfrepotes.fr' `
    --dashboard-port 8765
```

Par défaut, l’orchestrateur enchaîne le contrôle du clone, la détection phpBB, l’export et la conversion. L’import Discourse et la validation finale sont activés explicitement :

```powershell
python scripts/orchestrate_migration.py `
    --clone-path 'C:\chemin\choisi\Clone_2026' `
    --php 'C:\xampp\php\php.exe' `
    --base-url 'http://surfrepotes.fr' `
    --discourse-url 'http://localhost:3000' `
    --api-key '<CLE_API>' `
    --admin-email 'admin@example.com' `
    --import `
    --validate `
    --dashboard-port 8765
```

Suivi disponible pendant et après l’exécution :

- terminal : progression horodatée et code de chaque étape ;
- `data/logs/orchestrator.log` : journal textuel complet ;
- `data/orchestrator/state.json` : état machine des étapes, réutilisable avec `--resume` ;
- `data/orchestrator/dashboard.html` : tableau de bord graphique auto-actualisé ;
- `http://127.0.0.1:8765/dashboard.html` si `--dashboard-port` est fourni.

L’orchestrateur s’arrête sur la première erreur. `--resume` réutilise les étapes précédemment réussies. `--skip-files` permet un premier passage plus rapide sans copier les pièces jointes.

### Lanceur graphique

Pour éviter la saisie des chemins et options dans le terminal, lancer :

```powershell
python scripts/migration_gui.py
```

Sous Windows, il est aussi possible de double-cliquer sur [Lancer_Migration_GUI.bat](Lancer_Migration_GUI.bat) à la racine du projet. Le fichier utilise automatiquement `venv\Scripts\python.exe` lorsqu’il existe, puis démarre la fenêtre graphique.

La fenêtre permet de sélectionner graphiquement le chemin complet du clone FTP et `php.exe`, de renseigner les URLs, d’activer l’import ou la validation, puis de suivre le journal en direct. Le bouton **Ouvrir le dashboard** ouvre l’état graphique généré par l’orchestrateur.

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
