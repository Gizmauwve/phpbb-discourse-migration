# Rapport de Développement — Migration phpBB → Discourse

**Date de création** : 2026-08-28  
**Projet** : Surfrepotes — Migration forum phpBB 3.0.x vers Discourse  
**Source d’exemple** : `Clone/Input_27082026/www/forum/` (le chemin `Clone/Input_27082026` a été choisi lors de la copie FTP)
**Dépôt scripts** : `Travail/Source/phpbb-discourse-migration/`

---

## État global

| Étape | Tâche | Statut |
|-------|-------|--------|
| 0 | Environnement de développement | ✅ Opérationnel |
| 1 | Détection version phpBB | ⚪ Non démarré |
| 2 | Export données phpBB | 🟡 Prêt — base locale restaurée |
| 3 | Conversion format Discourse | ⚪ Non démarré |
| 4 | Déploiement Discourse local (Docker) | 🟡 Stack démarrée — wizard à terminer |
| 5 | Import dans Discourse | ⚪ Non démarré |
| 6 | Validation de la migration | ⚪ Non démarré |

---

## État des prérequis (28/08/2026)

| Prérequis | Version | Statut |
|-----------|---------|--------|
| Python | 3.10.9 | ✅ Installé |
| Docker Desktop | 4.88.1 | ✅ Installé (à démarrer) |
| pip / venv | — | ✅ Disponible |
| MariaDB/MySQL XAMPP | 10.x | ✅ Démarré localement |
| Dump SQL de la base phpBB | 22/04/2024 | ✅ Restauré localement |
| Base locale `surfrepotes` | — | ✅ 66 tables, 8 122 sujets |
| Apache + PHP XAMPP | PHP 8.2.12 | ✅ Site local accessible |
| Discourse local | Docker Compose | 🟡 Démarré, configuration web restante |

## Journal des opérations réalisées (28/08/2026)

### 1. Mise en ligne locale du clone

#### Deux copies à ne pas confondre

Deux chemins physiques sont utilisés pour ce site :

| Rôle | Chemin | Usage |
|------|--------|-------|
| Clone de référence | `<chemin-complet-du-clone-choisi-sur-le-FTP>/www` | Source à analyser, documenter et utiliser pour préparer la migration |
| Copie d’exécution XAMPP | `C:\xampp\htdocs\surfrepotes\www` | Copie effectivement servie par Apache et testée dans le navigateur |

Ces deux dossiers ne sont pas synchronisés automatiquement. Une modification dans la copie XAMPP ne modifie pas le clone de référence, et une nouvelle copie de `www` peut écraser les corrections locales déjà appliquées. Les fichiers `forum/config.php` et `.htaccess` ont notamment des contenus différents entre ces deux emplacements.

#### Copie du dossier `www`

Le dossier `www` du clone doit être copié dans le répertoire Apache de XAMPP avant de démarrer la navigation locale. Le chemin complet du clone (répertoire parent et nom du dossier) est choisi par l’opérateur lors de la récupération depuis le FTP. Le dépôt et la copie servie par Apache sont deux emplacements distincts :

```text
Source      : <chemin-complet-du-clone-choisi-sur-le-FTP>/www
Destination : C:\xampp\htdocs\surfrepotes\www
```

Commande PowerShell reproductible (`$clonePath` doit reprendre le chemin complet choisi lors de la copie FTP, jusqu’au dossier du clone) :

```powershell
$clonePath = '.\Clone\Input_27082026'
Copy-Item -Path (Join-Path $clonePath 'www') -Destination 'C:\xampp\htdocs\surfrepotes' -Recurse -Force
```

Après cette copie, reporter les adaptations de compatibilité PHP 8 indiquées plus loin et ne conserver dans `forum/config.php` que les identifiants locaux. Pour éviter toute ambiguïté, toujours vérifier le chemin du fichier modifié et tester ensuite `http://surfrepotes.fr/`.

Après la copie, vérifier que les éléments suivants existent dans la destination :

```text
C:\xampp\htdocs\surfrepotes\www\index.php
C:\xampp\htdocs\surfrepotes\www\forum\
C:\xampp\htdocs\surfrepotes\www\.htaccess
```

Les corrections locales et la restauration de la base doivent être appliquées à la copie effectivement servie par XAMPP. Si une nouvelle copie de `www` est réalisée, reporter ensuite les adaptations décrites dans les sections suivantes.

Le site est servi par Apache depuis :

```text
C:\xampp\htdocs\surfrepotes\www
```

Configuration nécessaire :

- fichier hosts Windows : `127.0.0.1 surfrepotes.fr` et `127.0.0.1 www.surfrepotes.fr` ;
- VirtualHost Apache dans `C:\xampp\apache\conf\extra\httpd-vhosts.conf` ;
- `DocumentRoot` : `C:/xampp/htdocs/surfrepotes/www` ;
- `AllowOverride All` pour autoriser le `.htaccess` ;
- Apache, PHP et MariaDB démarrés depuis XAMPP.

Le test de référence est :

```powershell
curl.exe -I http://surfrepotes.fr/
```

Résultat attendu : `HTTP/1.1 200 OK`, et non une redirection vers le site public.

### 2. Suppression de la redirection forcée vers la production

Le fichier `www/.htaccess` forçait auparavant toutes les requêtes HTTP vers `https://surfrepotes.fr`. Cette règle a été limitée aux hosts externes afin de conserver la navigation locale sur `http://surfrepotes.fr`.

Fichier modifié dans la copie XAMPP :

```text
C:\xampp\htdocs\surfrepotes\www\.htaccess
```

### 3. Compatibilité phpBB 3.0.x avec PHP 8

Le forum chargeait `includes/db/mysql.php`, qui appelle les fonctions supprimées `mysql_connect`, `mysql_query`, etc. Avec PHP 8, cela produisait : `mysql_connect function does not exist`.

Le pilote phpBB a été basculé vers `mysqli` dans :

```text
C:\xampp\htdocs\surfrepotes\www\forum\config.php
```

Configuration locale utilisée :

```php
$dbms = 'mysqli';
$dbhost = 'localhost';
$dbname = 'surfrepotes';
$dbuser = 'root';
$dbpasswd = '';
```

Ne jamais réutiliser les identifiants de production dans une copie locale ou dans un dépôt partagé. Les identifiants présents dans l’ancien clone doivent être considérés comme exposés et remplacés/rotés côté hébergement si nécessaire.

### 4. Restauration de la base phpBB

La sauvegarde retenue est :

```text
Clone/Input_27082026/www/forum/store/backup_1713797050_4e9b285ca9bbb87e.sql.gz
```

Elle correspond au dump du 22/04/2024. La procédure reproductible avec XAMPP est :

```powershell
& 'C:\xampp\mysql\bin\mysql.exe' -u root -e "CREATE DATABASE IF NOT EXISTS surfrepotes CHARACTER SET utf8 COLLATE utf8_general_ci;"
```

Puis décompresser le fichier gzip et importer son contenu SQL dans la base `surfrepotes`. Après restauration, vérifier les tables et la navigation :

```sql
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'surfrepotes';
SELECT COUNT(*) FROM surfrepotes.phpbb3_topics;
```

Valeurs observées : 66 tables et 8 122 sujets.

### 5. Corrections syntaxiques PHP des blocs de la page d’accueil

Les fichiers suivants utilisaient le short tag `<?` après une boucle `while`. Avec PHP 8 et `short_open_tag` désactivé, cela provoquait des erreurs `Unclosed '{'` lors de l’inclusion :

- `www/last_topics_opn.php` ;
- `www/last_sessions_opn.php` ;
- `www/last_trips_opn.php`.

Dans la copie XAMPP, chaque short tag a été remplacé par l’ouverture explicite `<?php`, compatible quelle que soit la valeur de `short_open_tag`.

Validation effectuée :

```powershell
& 'C:\xampp\php\php.exe' -l 'C:\xampp\htdocs\surfrepotes\www\last_topics_opn.php'
```

Résultat : `No syntax errors detected`.

### 6. Tests fonctionnels réalisés

```text
http://surfrepotes.fr/        -> 200, sans erreur SQL/PHP
http://surfrepotes.fr/forum/  -> 200, sans erreur SQL/PHP
```

Le contrôle de l’accueil après ces corrections ne détecte plus les messages `Undefined array key`, `Parse error`, `Fatal error`, `SQL ERROR` ou `mysqli_sql_exception`.

### 7. Compatibilité PHP 8 sur l’ouverture d’un sujet SEO

L’ouverture du sujet `viewtopic.php?t=10037` a révélé plusieurs incompatibilités supplémentaires dans les extensions phpBB SEO et dans le code phpBB 3.0.x :

- `phpbb_seo/phpbb_seo_class.php` : ajout d’un constructeur `__construct()` appelant l’ancien constructeur `phpbb_seo()` ; sans cela, les tableaux `RegEx`, `sftpl` et `url_replace` restaient vides ;
- `includes/utf/utf_normalizer.php` : méthodes de normalisation appelées statiquement rendues statiques (`nfc`, `nfkc`, `nfd`, `nfkd`, `cleanup`, `recompose`, `decompose`) ;
- `phpbb_seo/phpbb_seo_meta.php` : ajout d’un constructeur `__construct()` appelant `seo_meta()`, nécessaire pour initialiser `get_filter` avant `array_merge()` ;
- `includes/session.php` : ajout d’un constructeur `__construct()` appelant `user()`, nécessaire pour initialiser `lang_path` et charger `language/fr/common.php` ;
- `includes/functions_content.php` : correction de l’accès à une variable variable avec la syntaxe explicite `${$sort_ary['key']}` ;
- `forum/viewtopic.php` : appel explicite de `$user->setup('viewtopic')` après le démarrage de session.

Les fichiers ci-dessus ont été modifiés dans la copie servie par XAMPP. La validation syntaxique PHP est passée pour chaque fichier modifié.

La sauvegarde restaurée sélectionnait initialement `prosilver_se`, dont la copie locale ne contenait pas tous les templates nécessaires. La base locale a donc été réglée sur le style `prosilver` complet et le cache phpBB a été vidé. Ce réglage doit être reproduit uniquement dans une base locale de test, pas sur la base de production.

**État restant** : l’URL SEO est bien générée, mais le rendu du sujet doit encore être finalisé si phpBB affiche `template->_tpl_load_file(): File does not exist or is empty`. Vérifier alors la présence de `styles/prosilver/template/viewtopic_body.html`, la configuration des tables de styles restaurées et le cache `forum/cache/`.

## Reproduction pour un autre site phpBB

1. Copier le site dans `C:\xampp\htdocs\<nom-du-site>\www`.
2. Ajouter le nom local dans le fichier hosts Windows.
3. Créer un VirtualHost Apache correspondant et activer `AllowOverride All`.
4. Chercher dans `.htaccess`, les fichiers PHP et la configuration phpBB toute redirection ou URL canonique vers la production.
5. Avec PHP 7 ou supérieur, utiliser le pilote phpBB `mysqli` et non `mysql`.
6. Créer une base locale dédiée et restaurer un dump SQL correspondant à la version du site.
7. Adapter `forum/config.php` aux identifiants locaux, sans recopier les secrets de production.
8. Vérifier les constructeurs legacy des classes phpBB et des MODs (`user()`, `phpbb_seo()`, `seo_meta()`) et ajouter des constructeurs `__construct()` si PHP 8 ne les appelle plus.
9. Vérifier les appels statiques à des méthodes non statiques et les anciennes syntaxes de variables variables.
10. Tester le lint des fichiers PHP modifiés puis l’accueil, l’index du forum et une page de sujet SEO.
11. Vérifier les inclusions de la page d’accueil (`last_topics_opn.php`, `last_sessions_opn.php`, `last_trips_opn.php`) et remplacer les short tags PHP `<?` par `<?php`.
12. Seulement après ces contrôles, lancer l’export vers le projet de migration.

La copie actuellement servie par XAMPP est distincte de la copie source située dans `$clonePath`. Pour reproduire exactement l’environnement, reporter les corrections suivantes dans la copie source avant de lancer une nouvelle migration : `.htaccess`, `forum/config.php`, `last_topics_opn.php`, `last_sessions_opn.php`, `last_trips_opn.php`, `forum/includes/db/dbal.php`, les fichiers de compatibilité SEO/UTF/session et `forum/viewtopic.php`. Après chaque recopie vers XAMPP, réappliquer la configuration locale de `forum/config.php` et vérifier la base utilisée. Ne pas versionner les mots de passe locaux ou de production.

---

## État des scripts

### `migration_gui.py`
- **Rôle** : Fournit une interface graphique native pour sélectionner le clone FTP, choisir `php.exe`, renseigner les URLs et lancer l’orchestrateur.
- **Entrée utilisateur** : Sélecteurs de fichiers/dossiers, champs de formulaire et cases à cocher ; aucun chemin de clone n’est imposé.
- **Sortie** : Journal de l’orchestrateur affiché en direct et accès au dashboard HTML.
- **Lancement** : `python scripts/migration_gui.py`
- **Sécurité** : la clé API est saisie dans un champ masqué et l’orchestrateur la masque dans son journal ; l’import reste désactivé tant que la case n’est pas cochée.
- **Statut** : ✅ Créé et compilé ; l’exécution de la fenêtre doit être faite dans une session Windows interactive.

### `Lancer_Migration_GUI.bat`
- **Rôle** : Lanceur Windows par double-clic de l’interface graphique.
- **Fonctionnement** : se place dans le répertoire du projet, utilise le venv local s’il existe et démarre `scripts/migration_gui.py`.
- **Usage** : double-cliquer sur `Lancer_Migration_GUI.bat` à la racine de `Travail/Source/phpbb-discourse-migration`.
- **Statut** : ✅ Créé ; le lancement est interactif et doit être effectué sur Windows.

### `orchestrate_migration.py`
- **Rôle** : Découvre les éléments du clone FTP, enchaîne les contrôles, la détection, l’export, la conversion, puis éventuellement l’import et la validation.
- **Entrée** : Chemin complet du clone (`--clone-path`), jusqu’au dossier qui contient `www`.
- **Sorties** : Journal terminal, `data/logs/orchestrator.log`, `data/orchestrator/state.json` et `data/orchestrator/dashboard.html`.
- **Monitoring graphique** : `--dashboard-port 8765`, puis `http://127.0.0.1:8765/dashboard.html`.
- **Sécurité d’exécution** : l’import et la validation sont désactivés par défaut ; utiliser `--import` et `--validate` explicitement. La clé API n’est pas écrite dans le journal.
- **Reprise** : `--resume` réutilise les étapes déjà réussies.
- **Statut** : ✅ Créé et testé ; sur le clone actuel, il découvre correctement le chemin et s’arrête sur la détection tant que `forum/config.php` pointe vers la base FTP distante.
- **Commande minimale** :
  ```powershell
  python scripts/orchestrate_migration.py --clone-path 'C:\chemin\complet\du\clone' --php 'C:\xampp\php\php.exe' --base-url 'http://surfrepotes.fr' --dashboard-port 8765
  ```

### `detect_version.py`
- **Rôle** : Détecte la version phpBB installée (2.0 / 3.0 / 3.1 / 3.2) et génère `config/version.json`
- **Entrée** : Répertoire source phpBB (`--source`)
- **Sortie** : `config/version.json`
- **Dépendances** : `pymysql`, `python-dotenv`
- **Statut** : ⚪ Non exécuté
- **Commande** :
  ```bash
  $clonePath = '..\..\..\Clone\Input_27082026'
  $phpbbPath = Join-Path $clonePath 'www\forum'
  python scripts/detect_version.py --source $phpbbPath --output config/version.json --verbose
  ```

---

### `export_phpbb.py`
- **Rôle** : Exporte les données phpBB (utilisateurs, catégories, sujets, posts, pièces jointes) en fichiers JSON
- **Entrée** : Répertoire phpBB + accès MySQL (via `config.php` ou `.env`)
- **Sortie** : `data/export/*.json` + `data/export/files/`
- **Dépendances** : `pymysql`, `python-dotenv`
- **Statut** : 🔴 Bloqué — accès MySQL requis (dump SQL ou base locale à restaurer)
- **Commande** :
  ```bash
  python scripts/export_phpbb.py --source $phpbbPath --output ./data/export --verbose
  ```
- **Bloquant** : La base `surfrepodivers` doit être restaurée localement, ou un dump SQL doit être disponible

---

### `convert_data.py`
- **Rôle** : Convertit les JSON phpBB en format NDJSON Discourse (remapping IDs, conversion BBCode → Markdown)
- **Entrée** : `data/export/*.json`
- **Sortie** : `data/converted/*.ndjson`
- **Dépendances** : stdlib uniquement
- **Statut** : ⚪ En attente de l'étape export
- **Commande** :
  ```bash
  python scripts/convert_data.py --input ./data/export --output ./data/converted --verbose
  ```

---

### `import_discourse.py`
- **Rôle** : Importe les données converties dans une instance Discourse via son API REST
- **Entrée** : `data/converted/*.ndjson`
- **Sortie** : Forum Discourse peuplé sur `http://localhost:3000`
- **Dépendances** : `requests`, `tqdm`
- **Statut** : 🔴 Bloqué — nécessite Docker + Discourse opérationnel
- **Commande** :
  ```bash
  python scripts/import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key <CLE> --admin-email <EMAIL>
  ```

---

### `validate_migration.py`
- **Rôle** : Compare les données phpBB source et le Discourse cible — produit un rapport HTML de validation
- **Entrée** : Répertoire phpBB + URL Discourse
- **Sortie** : `data/logs/validation.html`
- **Dépendances** : `requests`
- **Statut** : ⚪ En attente des étapes précédentes
- **Commande** :
  ```bash
  python scripts/validate_migration.py --phpbb $phpbbPath --discourse http://localhost:3000 --verbose
  ```

---

## Conversations / Tâches

### TÂCHE-01 — Finaliser l'environnement de développement
**Priorité** : 🔴 Haute (bloquante pour tout)  
**Description** :  
Installer Docker Desktop et créer l'environnement Python virtuel avec toutes les dépendances.

**Actions à faire** :
1. Installer Docker Desktop : `winget install Docker.DockerDesktop` puis redémarrer
2. Créer le venv :
   ```powershell
   cd Travail\Source\phpbb-discourse-migration
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Vérifier : `python -c "import pymysql, requests; print('OK')"`

**Statut** : ✅ Terminé — Docker Desktop 4.88.1 fonctionnel, venv créé et dépendances installées.

---

### TÂCHE-02 — Localiser ou restaurer la base de données phpBB
**Priorité** : 🔴 Haute (bloquante pour l'export)  
**Description** :  
Le script `export_phpbb.py` lit `config.php` dans le répertoire phpBB pour se connecter à la base MySQL `surfrepodivers`. Sans accès à cette base, l'export est impossible.

**Actions à faire** :
1. Vérifier si un dump SQL existe dans le projet ou sur un support externe
2. Si dump disponible : installer MySQL local et restaurer :
   ```bash
   mysql -u root -p -e "CREATE DATABASE surfrepodivers;"
   mysql -u root -p surfrepodivers < dump_surfrepodivers.sql
   ```
3. Si pas de dump : vérifier si `connexion_surfrepodivers.php` peut donner accès au serveur original `mysql5-29`
4. Mettre à jour `config.php` du forum pour pointer vers `localhost`

**Fichiers concernés** :
- `$clonePath/www/connexion_surfrepodivers.php` — connexion actuelle sur `mysql5-29`
- `$clonePath/www/forum/config.php` — config utilisée par export_phpbb.py

**Statut** : ✅ Terminé pour le clone local — MariaDB XAMPP contient la base `surfrepotes` restaurée depuis le dump du 22/04/2024.

**Attention** : la copie déployée dans `C:\xampp\htdocs\surfrepotes\www` utilise la configuration locale. La copie source `Clone/<nom-du-clone-choisi-sur-le-FTP>/www/forum/config.php` peut conserver l’ancienne configuration d’hébergement et doit être adaptée avant une nouvelle exécution locale.

---

### TÂCHE-03 — Détecter et confirmer la version phpBB
**Priorité** : 🟡 Moyenne  
**Description** :  
Exécuter `detect_version.py` pour confirmer la version exacte du forum (attendu : 3.0.x) et générer `config/version.json` utilisé par les scripts suivants.

**Dépend de** : TÂCHE-01 (venv), TÂCHE-02 (accès DB)

**Commande** :
```powershell
cd Travail\Source\phpbb-discourse-migration
.\venv\Scripts\Activate.ps1
$clonePath = '..\..\..\Clone\Input_27082026'
$phpbbPath = Join-Path $clonePath 'www\forum'
python scripts/detect_version.py --source $phpbbPath --output config/version.json --verbose
```

**Statut** : ⚪ Non démarré

---

### TÂCHE-04 — Exporter les données phpBB
**Priorité** : 🟡 Moyenne  
**Description** :  
Exécuter `export_phpbb.py` pour extraire tous les utilisateurs, catégories, sujets, posts et pièces jointes du forum phpBB vers des fichiers JSON dans `data/export/`.

**Dépend de** : TÂCHE-01, TÂCHE-02, TÂCHE-03

**Commande** :
```powershell
python scripts/export_phpbb.py --source $phpbbPath --output ./data/export --verbose
```

**Fichiers attendus en sortie** :
- `data/export/users.json`
- `data/export/categories.json`
- `data/export/topics.json`
- `data/export/posts.json`
- `data/export/attachments.json`
- `data/export/files/` (avatars + pièces jointes)

**Statut** : ⚪ Non démarré

---

### TÂCHE-05 — Convertir les données au format Discourse
**Priorité** : 🟢 Basse (séquentielle)  
**Description** :  
Exécuter `convert_data.py` pour transformer les JSON phpBB en NDJSON Discourse. Cette étape effectue le remapping des IDs, la conversion du BBCode en Markdown et la réorganisation des fichiers.

**Dépend de** : TÂCHE-04

**Commande** :
```powershell
python scripts/convert_data.py --input ./data/export --output ./data/converted --verbose
```

**Statut** : ⚪ Non démarré

---

### TÂCHE-06 — Déployer Discourse localement (Docker)
**Priorité** : 🔴 Haute (parallèle aux autres)  
**Description** :  
Lancer l'instance Discourse locale via Docker Compose (PostgreSQL + Redis + Discourse). Compléter le wizard de configuration et générer une clé API pour l'import.

**Dépend de** : TÂCHE-01 (Docker installé)

**Commandes** :
```powershell
cd Travail\Source\phpbb-discourse-migration
docker-compose up -d
# Puis ouvrir http://localhost:3000 et compléter le setup
```

**Actions post-démarrage** :
1. Accéder à http://localhost:3000 → compléter le wizard
2. Aller dans Admin > API > Générer une clé globale
3. Noter la clé API et l'email admin pour TÂCHE-07

**Statut** : 🟡 Partiellement terminé — Docker Compose démarré avec succès ; le wizard Discourse et la génération de la clé API restent à faire.

---

### TÂCHE-07 — Importer dans Discourse
**Priorité** : 🟢 Basse (séquentielle)  
**Description** :  
Exécuter `import_discourse.py` pour charger les données converties dans l'instance Discourse locale via son API REST, par lots de 100 objets.

**Dépend de** : TÂCHE-05, TÂCHE-06

**Commande** :
```powershell
python scripts/import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key <CLE_API> --admin-email <EMAIL> --verbose
```

**Statut** : ⚪ Non démarré

---

### TÂCHE-08 — Valider la migration
**Priorité** : 🟢 Basse (séquentielle)  
**Description** :  
Exécuter `validate_migration.py` pour comparer le contenu phpBB source et le Discourse cible. Produit un rapport HTML de validation avec les éventuels écarts.

**Dépend de** : TÂCHE-07

**Commande** :
```powershell
python scripts/validate_migration.py --phpbb $phpbbPath --discourse http://localhost:3000 --verbose
```

**Rapport de sortie** : `data/logs/validation.html`

**Statut** : ⚪ Non démarré

---

## Chemin critique

```
TÂCHE-01 (venv + Docker)
    ├──► TÂCHE-02 (base MySQL)
    │        └──► TÂCHE-03 (detect_version)
    │                  └──► TÂCHE-04 (export)
    │                            └──► TÂCHE-05 (convert)
    │                                      └──► TÂCHE-07 (import)
    │                                                 └──► TÂCHE-08 (validate)
    └──► TÂCHE-06 (Docker Discourse) ──────────────────────┘
```

**Prochaine action immédiate** : reporter les corrections de compatibilité dans la copie source, exécuter `detect_version.py`, puis lancer l’export phpBB depuis la base locale restaurée. En parallèle, terminer le wizard Discourse et générer la clé API pour l’import.
