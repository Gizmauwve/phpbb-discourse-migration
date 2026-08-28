# 📋 Recette de Validation - Migration phpBB → Discourse

Liste complète des vérifications avant, pendant et après la migration.

## ✅ Phase 1 : Préparation

### Infrastructure
- [ ] Docker & Docker Compose installés
- [ ] Python 3.8+ disponible
- [ ] ~20 GB d'espace disque libre
- [ ] Accès au répertoire phpBB local (`../Input`)
- [ ] Accès MySQL/MariaDB (ou dump SQL disponible)

### Données phpBB
- [ ] Sauvegarde complète effectuée
- [ ] Version phpBB confirmée (3.0.x)
- [ ] Nombre d'utilisateurs identifié
- [ ] Nombre de catégories identifié
- [ ] Nombre de sujets identifié
- [ ] Nombre de posts identifié
- [ ] Volume des pièces jointes mesuré
- [ ] État de la base de données vérifié (intégrité)

## ✅ Phase 2 : Configuration initiale

### Discourse local
- [ ] `docker-compose up -d` lancé avec succès
- [ ] Discourse accessible sur http://localhost:3000
- [ ] Setup wizard complété
- [ ] Compte admin créé
- [ ] API key générée et notée

### Environnement Python
- [ ] Environnement virtuel créé : `python -m venv venv`
- [ ] Activé : `source venv/bin/activate`
- [ ] Dépendances installées : `pip install -r requirements.txt`
- [ ] Fichier `.env` créé avec configurations (si nécessaire)

## ✅ Phase 3 : Export phpBB

### Exécution
```bash
python scripts/export_phpbb.py --source ../Input --output ./data/export --verbose
```

**Validations** :
- [ ] Script s'exécute sans erreur
- [ ] Fichiers JSON créés :
  - [ ] `data/export/users.json`
  - [ ] `data/export/categories.json`
  - [ ] `data/export/topics.json`
  - [ ] `data/export/posts.json`
  - [ ] `data/export/attachments.json`
- [ ] Dossier `data/export/files/` contient les pièces jointes
- [ ] Fichier log créé : `data/logs/export_phpbb.log`

### Vérifications de contenu
- [ ] Nombre d'utilisateurs dans `users.json` correct
- [ ] Nombre de catégories dans `categories.json` correct
- [ ] Nombre de sujets dans `topics.json` correct
- [ ] Nombre de posts dans `posts.json` correct
- [ ] Tous les fichiers uploadés présents dans `data/export/files/`
- [ ] Pas de fichiers corrompus (vérifier tailles)

## ✅ Phase 4 : Conversion aux formats Discourse

### Exécution
```bash
python scripts/convert_data.py --input ./data/export --output ./data/converted --verbose
```

**Validations** :
- [ ] Script s'exécute sans erreur
- [ ] Fichiers NDJSON créés :
  - [ ] `data/converted/users.ndjson`
  - [ ] `data/converted/categories.ndjson`
  - [ ] `data/converted/topics.ndjson`
  - [ ] `data/converted/posts.ndjson`
- [ ] Dossier `data/converted/files/` organisé correctement
- [ ] Fichier log créé : `data/logs/convert_data.log`

### Vérifications de format
- [ ] Chaque ligne NDJSON est du JSON valide
- [ ] Usernames uniques et valides
- [ ] Catégories mappées correctement
- [ ] Topics et posts avec relations parent correctes
- [ ] Timestamps au bon format ISO 8601
- [ ] HTML/Markdown correctement échappé

## ✅ Phase 5 : Import dans Discourse

### Test dry-run d'abord
```bash
python scripts/import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key YOUR_API_KEY --admin-email admin@example.com --dry-run
```

- [ ] Dry-run s'exécute sans erreur
- [ ] Rapport généré sans problèmes critiques

### Import réel
```bash
python scripts/import_discourse.py --source ./data/converted --target http://localhost:3000 --api-key YOUR_API_KEY --admin-email admin@example.com
```

**Validations** :
- [ ] Import s'exécute sans erreur fatale
- [ ] Fichier log créé : `data/logs/import_discourse.log`
- [ ] Barre de progression affichée
- [ ] Pas de timeout lors de l'import

### Dans Discourse UI
- [ ] Tous les utilisateurs importés (vérifier count)
- [ ] Tous les utilisateurs ont des avatars (si applicable)
- [ ] Toutes les catégories créées
- [ ] Tous les sujets créés avec le bon nombre de réponses
- [ ] Tous les posts visibles avec le bon contenu
- [ ] Les pièces jointes téléchargées et accessibles
- [ ] Les dates de création/modification correctes

## ✅ Phase 6 : Validation complète

### Exécution du script de validation
```bash
python scripts/validate_migration.py --phpbb ../Input --discourse http://localhost:3000 --verbose
```

**Rapports générés** :
- [ ] `data/logs/validation.html` créé et consultable
- [ ] Rapport HTML complet sans erreurs

### Validations unitaires
- [ ] Nombre total d'utilisateurs : phpBB = Discourse
- [ ] Nombre total de catégories : phpBB = Discourse
- [ ] Nombre total de sujets : phpBB = Discourse
- [ ] Nombre total de posts : phpBB = Discourse
- [ ] Aucun post orphelin (sans topic parent)
- [ ] Aucun utilisateur sans email valide
- [ ] Tous les avatars téléchargés
- [ ] Toutes les images inline présentes
- [ ] Pas de doublons
- [ ] Pas de données tronquées

### Tests de régression
- [ ] Recherche fonctionne (chercher un mot dans un post)
- [ ] Catégories affichent le bon nombre de sujets
- [ ] Utilisateurs peuvent se connecter
- [ ] Permissions correctes (modos, admins, etc.)
- [ ] Notifications fonctionnent
- [ ] Pagination des sujets fonctionne

## ✅ Phase 7 : Tests manuels détaillés

### Navigation
- [ ] Catégories affichées correctement
- [ ] Lien vers sujets fonctionnels
- [ ] Affichage des sujets complet
- [ ] Affichage des posts avec formatting original
- [ ] Pagination fonctionne (50+ posts)
- [ ] Recherche globale fonctionne
- [ ] Recherche par catégorie fonctionne

### Contenu
- [ ] BBCode phpBB converti en Markdown Discourse
- [ ] Images inline affichées
- [ ] Citations formatées correctement
- [ ] Listes à puces/numérotées correctes
- [ ] Tableaux affichés correctement (si applicable)
- [ ] Code blocks avec syntaxe highlight

### Utilisateurs
- [ ] Profils affichent les informations correctes
- [ ] Avatars affichés
- [ ] Nombre de posts correct par utilisateur
- [ ] Dates de jointure correctes
- [ ] Ancien contenu attribué aux bons utilisateurs

### Pièces jointes
- [ ] Fichiers téléchargeables
- [ ] Images inline visibles
- [ ] Tailles de fichiers correctes
- [ ] Permissions d'accès correctes
- [ ] Pas de liens cassés

## ✅ Phase 8 : Performance et optimisation

- [ ] Les pages se chargent rapidement (< 2s)
- [ ] Pas de requêtes N+1
- [ ] Base de données Discourse saine (`./rake db:validate_timestamps`)
- [ ] Indexation Discourse complète (`./rake search:index`)
- [ ] Cache chaud et optimal

## ✅ Phase 9 : Documentation et sign-off

### Documentation
- [ ] README.md complété avec spécificités
- [ ] Logs archivés pour référence future
- [ ] Mappages utilisateurs documentés (si modifications)
- [ ] Problèmes connus documentés
- [ ] Scripts testés et reproductibles

### Sign-off
- [ ] Propriétaire du forum a validé le contenu
- [ ] Aucun data loss accepté
- [ ] Migration approuvée pour production (si applicable)
- [ ] Plan de roll-back documenté

## 🐛 Problèmes courants

### Erreurs d'export
| Erreur | Cause | Solution |
|--------|-------|----------|
| `FileNotFoundError: config.php` | Mauvais chemin `--source` | Vérifie le chemin du répertoire phpBB |
| `ConnectionRefusedError` | MySQL non accessible | Démarre MySQL ou fournis les identifiants |
| `UnicodeDecodeError` | Encodage incompatible | Ajoute `--encoding utf-8` |

### Erreurs de conversion
| Erreur | Cause | Solution |
|--------|-------|----------|
| `KeyError: 'username'` | Données malformées | Vérifiez l'export, utilisez `--debug` |
| `ValueError: invalid timestamp` | Dates invalides | Corrigez manuellement ou utilisez `--skip-invalid` |

### Erreurs d'import
| Erreur | Cause | Solution |
|--------|-------|----------|
| `401 Unauthorized` | API key invalide | Régénérez la clé dans Discourse |
| `Timeout` | Données trop volumineuses | Réduisez `--batch-size` |
| `Duplicate key` | Données dupliquées | Nettoyez Discourse avec `./rake db:reset` |

## 📊 Métriques de succès

```
PhpBB → Discourse
Utilisateurs : ____ → ____ ✅
Catégories  : ____ → ____ ✅
Sujets      : ____ → ____ ✅
Posts       : ____ → ____ ✅
Pièces jointes : ____ GO → ____ GO ✅
Tems total  : _____ heures ✅
```

---

**Migration réussie ! 🎉**
