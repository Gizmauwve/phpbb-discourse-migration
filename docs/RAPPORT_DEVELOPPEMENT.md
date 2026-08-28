# Rapport de Développement — Migration phpBB → Discourse

**Date de création** : 2026-08-28  
**Projet** : Surfrepotes — Migration forum phpBB 3.0.x vers Discourse  
**Source** : `Clone/Input_27082026/www/forum/`  
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

### 5. Correction syntaxique PHP ponctuelle

Le fichier `www/last_topics_opn.php` utilisait le short tag `<?` après la boucle `while`. Il a été remplacé par l’ouverture explicite `<?php`, compatible quelle que soit la valeur de `short_open_tag`.

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

## Reproduction pour un autre site phpBB

1. Copier le site dans `C:\xampp\htdocs\<nom-du-site>\www`.
2. Ajouter le nom local dans le fichier hosts Windows.
3. Créer un VirtualHost Apache correspondant et activer `AllowOverride All`.
4. Chercher dans `.htaccess`, les fichiers PHP et la configuration phpBB toute redirection ou URL canonique vers la production.
5. Avec PHP 7 ou supérieur, utiliser le pilote phpBB `mysqli` et non `mysql`.
6. Créer une base locale dédiée et restaurer un dump SQL correspondant à la version du site.
7. Adapter `forum/config.php` aux identifiants locaux, sans recopier les secrets de production.
8. Tester le lint des fichiers PHP modifiés puis l’accueil, l’index du forum et une page de sujet.
9. Seulement après ces contrôles, lancer l’export vers le projet de migration.

La copie actuellement servie par XAMPP est distincte de la copie versionnée sous `Clone/Input_27082026`. Pour reproduire exactement l’environnement, reporter les trois corrections suivantes dans la copie source avant de lancer une nouvelle migration : `.htaccess`, `forum/config.php` et `last_topics_opn.php`. Ne pas versionner les mots de passe locaux ou de production.

---

## État des scripts

### `detect_version.py`
- **Rôle** : Détecte la version phpBB installée (2.0 / 3.0 / 3.1 / 3.2) et génère `config/version.json`
- **Entrée** : Répertoire source phpBB (`--source`)
- **Sortie** : `config/version.json`
- **Dépendances** : `pymysql`, `python-dotenv`
- **Statut** : ⚪ Non exécuté
- **Commande** :
  ```bash
  python scripts/detect_version.py --source ../../Clone/Input_27082026/www/forum --output config/version.json --verbose
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
  python scripts/export_phpbb.py --source ../../Clone/Input_27082026/www/forum --output ./data/export --verbose
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
  python scripts/validate_migration.py --phpbb ../../Clone/Input_27082026/www/forum --discourse http://localhost:3000 --verbose
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
- `Clone/Input_27082026/www/connexion_surfrepodivers.php` — connexion actuelle sur `mysql5-29`
- `Clone/Input_27082026/www/forum/config.php` — config utilisée par export_phpbb.py

**Statut** : ✅ Terminé pour le clone local — MariaDB XAMPP contient la base `surfrepotes` restaurée depuis le dump du 22/04/2024.

**Attention** : la copie déployée dans `C:\xampp\htdocs\surfrepotes\www` utilise la configuration locale. La copie source `Clone/Input_27082026/www/forum/config.php` conserve encore l’ancienne configuration d’hébergement et doit être adaptée avant une nouvelle exécution locale.

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
python scripts/detect_version.py --source ..\..\Clone\Input_27082026\www\forum --output config/version.json --verbose
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
python scripts/export_phpbb.py --source ..\..\Clone\Input_27082026\www\forum --output ./data/export --verbose
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
python scripts/validate_migration.py --phpbb ..\..\Clone\Input_27082026\www\forum --discourse http://localhost:3000 --verbose
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
