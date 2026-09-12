# phpBB → Discourse Migration Manual

This document describes the current migration workflow for the Surfrepotes forum, moving from **phpBB 3.0.13-PL1** to **Discourse**.

The previous forum-simulation approach based on an FTP clone, XAMPP, and a local rehosting of phpBB is now considered legacy context. The active migration process is centered on the **Discourse phpBB importer/plugin**, a restored phpBB database, and a small set of helper scripts that prepare, run, and validate the migration.

---

## 1. Purpose of the migration

The goal is to migrate the Surfrepotes phpBB forum into Discourse in a way that is:

- repeatable;
- traceable;
- testable locally;
- safe for the original source data;
- easy to validate and rerun if needed.

The migration is split into clear phases:

1. prepare the local environment;
2. restore the phpBB SQL dump into MariaDB;
3. connect the Discourse importer to that source;
4. run the import;
5. validate the imported forum;
6. optionally handle files and media later.

---

## 2. Required environment

### 2.1 Windows host

The process starts on Windows because the source dump and the main launcher are stored there.

Required components:

- Windows 10 or Windows 11
- Docker Desktop
- WSL2
- VS Code
- VS Code Dev Containers extension

Windows is used to:

- launch Docker Desktop;
- run the batch launcher;
- access the SQL dump stored on `C:`;
- open the Discourse project in VS Code through WSL.

---

### 2.2 WSL2 Ubuntu

The working shell environment is Ubuntu under WSL2.

This environment is used to:

- run shell scripts;
- communicate with Docker;
- compute checksums;
- open the Discourse workspace in VS Code;
- connect Docker containers to the same network.

Relevant paths:

- Discourse repository in WSL: `/home/flore/discourse`
- Windows C: drive in WSL: `/mnt/c`

---

### 2.3 Docker

Docker is required for:

- the Discourse development stack;
- the temporary MariaDB container used to restore the phpBB dump;
- the shared Docker network between the two containers.

You must have Docker Desktop running before the migration can proceed.

---

### 2.4 Discourse Dev Container

The actual import is run inside the Discourse Dev Container.

That container is where you:

- install Ruby/native dependencies if needed;
- run `bundle install`;
- verify network access to MariaDB;
- execute the Discourse phpBB importer.

---

## 3. Repository layout and script inventory

This repository contains both migration documentation and helper scripts.

### 3.1 Repository root scripts

These scripts live at the **root of this repository**:

- `lancer_discourse.bat`
- `surfrepotes-migration.sh`
- `surfrepotes.yml`
- `setup-devcontainer.sh`
- `run-surfrepotes.sh`

### 3.2 Discourse importer files

These files live inside the **Discourse repository**, not this repo:

- `script/import_scripts/phpbb3.rb`
- `script/import_scripts/phpbb3/surfrepotes.yml`

The helper runner `run-surfrepotes.sh` points to these files.

---

## 4. Script details

### 4.1 `lancer_discourse.bat`
**Location:** repository root

This is the main Windows entry script.

#### Responsibilities

- start Docker Desktop;
- wait until Docker is ready;
- verify the SQL dump exists;
- compute the dump SHA-256 hash;
- create or start the temporary MariaDB container `phpbb-mariadb`;
- import the dump only if needed;
- create or reuse the Docker network `phpbb_import`;
- open the Discourse project in VS Code through WSL;
- provide instructions for the Dev Container and the import step.

#### Why it matters

This script prepares the local migration environment and avoids reimporting the same SQL dump unnecessarily.

#### Important paths used by the script

- Windows source dump:
  `C:\Users\flore\source\repos\Surfrepotes\Travail\Input\surfrepotes_mysql_db.sql`

- WSL source dump:
  `/mnt/c/Users/flore/source/repos/Surfrepotes/Travail/Input/surfrepotes_mysql_db.sql`

- Local WSL copy of the dump:
  `/home/flore/discourse/surfrepotes_mysql_db.sql`

- SHA-256 state file:
  `/home/flore/discourse/.surfrepotes_sql.sha256`

#### Important containers and values

- MariaDB container: `phpbb-mariadb`
- MariaDB root password: `phpbbroot`
- MariaDB database: `surfrepotes`
- Docker network: `phpbb_import`

---

### 4.2 `surfrepotes-migration.sh`
**Location:** repository root

This is the WSL helper script that prepares Docker networking.

#### Responsibilities

- ensure the Docker network `phpbb_import` exists;
- verify that `phpbb-mariadb` is running;
- detect the Discourse Dev Container;
- connect both containers to the shared network.

#### Why it matters

The importer must be able to resolve `phpbb-mariadb` by hostname from inside the Dev Container.

#### Usage

Run it from WSL after the Dev Container exists, or when you need to repair the Docker network setup.

---

### 4.3 `surfrepotes.yml`
**Location:** repository root

This is the importer configuration file.

#### Responsibilities

- define the MariaDB connection;
- define the phpBB table prefix;
- define the Discourse target URL;
- enable or disable import features;
- optionally define file locations for avatars, attachments, and smilies.

#### Important settings

- `database.host: phpbb-mariadb`
- `database.port: 3306`
- `database.username: root`
- `database.password: phpbbroot`
- `database.schema: surfrepotes`
- `database.table_prefix: phpbb3_`
- `import.phpbb_base_dir: /workspace/discourse/phpbb_data`
- `import.site_prefix.original: www.surfrepotes.fr/forum`
- `import.site_prefix.new: http://localhost:3000`

#### Import toggles currently set

Enabled:

- `private_messages: true`
- `polls: true`

Disabled for the first pass:

- `attachments: false`
- `avatars.uploaded: false`
- `avatars.gallery: false`
- `avatars.remote: false`
- `passwords: false`
- `likes: false`

#### Why it matters

This file controls what the importer does and what data source it uses.

---

### 4.4 `setup-devcontainer.sh`
**Location:** repository root

This script prepares the Discourse Dev Container.

#### Responsibilities

- update apt package lists;
- install system packages required by the importer;
- install MariaDB development headers;
- install build tools;
- run `bundle install`.

#### Usage

Run it inside the Dev Container before running the import if dependencies are missing.

---

### 4.5 `run-surfrepotes.sh`
**Location:** repository root

This script launches the actual import.

#### Responsibilities

- verify that the importer YAML file exists;
- invoke the Discourse importer through Ruby;
- run the phpBB → Discourse import using the current config.

#### It runs this command internally

```bash
bundle exec ruby script/import_scripts/phpbb3.rb script/import_scripts/phpbb3/surfrepotes.yml
```

#### Why it matters

This is the script that actually starts the migration inside the Discourse environment.

---

## 5. Procedure overview

The full migration should be executed in the following order.

---

### Step 1 — Start Docker Desktop

On Windows, start Docker Desktop and wait until it is ready.

You can let `lancer_discourse.bat` do this automatically.

---

### Step 2 — Launch the preparation batch file

Run:

```bat
lancer_discourse.bat
```

This will:

1. start Docker Desktop;
2. verify the dump exists;
3. compute its SHA-256 hash;
4. create or reuse `phpbb-mariadb`;
5. import the SQL dump if needed;
6. ensure `phpbb_import` exists;
7. open the Discourse repository in VS Code.

---

### Step 3 — Open the project in VS Code

The batch file opens the project from WSL into VS Code.

Then:

- reopen the project in the **Dev Container**;
- wait for the container to finish building;
- open a terminal inside the container.

This step is required because the import is executed from the Dev Container, not from plain Windows or plain WSL.

---

### Step 4 — Prepare the Dev Container

Inside the Dev Container, run:

```bash
./setup-devcontainer.sh
```

This installs missing native dependencies and Ruby gems.

If everything is already installed, this step may complete quickly.

---

### Step 5 — Confirm database reachability

Inside the Dev Container, check that the MariaDB container is visible:

```bash
getent hosts phpbb-mariadb
```

If this does not resolve, the Docker network is not ready yet.

In that case, return to WSL and run:

```bash
./surfrepotes-migration.sh
```

This connects the containers to the shared network.

---

### Step 6 — Validate the importer configuration

Review `surfrepotes.yml` and confirm:

- MariaDB host is `phpbb-mariadb`;
- schema is `surfrepotes`;
- prefix is `phpbb3_`;
- target URL is `http://localhost:3000`;
- `phpbb_base_dir` points to `/workspace/discourse/phpbb_data`.

For the first migration test, keep file-related options disabled unless you are explicitly testing files.

---

### Step 7 — Run the first controlled import

From the Dev Container, launch:

```bash
./run-surfrepotes.sh
```

or directly:

```bash
bundle exec ruby script/import_scripts/phpbb3.rb script/import_scripts/phpbb3/surfrepotes.yml
```

#### What to watch during the import

- MariaDB connection errors;
- category mapping problems;
- missing parent posts;
- skipped users;
- import warnings related to polls or private messages;
- unexpected file or attachment errors.

The first run should be treated as a controlled import test.

---

### Step 8 — Inspect the import result

After the import finishes, check the Discourse forum in the browser.

Validate at least:

- users;
- categories;
- topics;
- posts;
- private messages;
- timestamps;
- internal links;
- overall forum structure.

If the result is acceptable, you can keep the same configuration and rerun only if needed.

---

### Step 9 — Optional file and media handling

Only after the core forum data is working should you consider enabling media-related options.

Possible file types:

- attachments;
- avatars;
- smilies;
- inline images.

If you want to use files, the importer expects a phpBB data directory under:

```text
/workspace/discourse/phpbb_data
```

You can then enable the corresponding options in `surfrepotes.yml`.

---

### Step 10 — Final validation

Once the import is complete, confirm:

- the forum opens normally in Discourse;
- the main counts are coherent;
- posts and topics render correctly;
- usernames are mapped as expected;
- private messages are present if enabled;
- file uploads work if you enabled them;
- the local forum is usable at `http://localhost:3000`.

---

## 6. Database preparation flow

### 6.1 Verify the source dump

The source SQL dump is:

```text
C:\Users\flore\source\repos\Surfrepotes\Travail\Input\surfrepotes_mysql_db.sql
```

and in WSL:

```text
/mnt/c/Users/flore/source/repos/Surfrepotes/Travail/Input/surfrepotes_mysql_db.sql
```

The launcher refuses to continue if the file is missing.

---

### 6.2 Compute and store the hash

The SHA-256 hash is used to detect whether the dump changed.

If the hash is unchanged and the target database already exists, the script avoids doing a full reimport.

---

### 6.3 Restore MariaDB if necessary

The temporary database container is:

```text
phpbb-mariadb
```

It is created with:

- `MARIADB_ROOT_PASSWORD=phpbbroot`
- `MARIADB_DATABASE=surfrepotes`

If the SQL dump changes, the launcher can rebuild the database and import it again.

---

### 6.4 Keep the database isolated

The MariaDB instance is only a temporary migration source.

It is not the final production database.

---

## 7. Docker network setup

The shared network used by the migration is:

```text
phpbb_import
```

### Why it is required

The Discourse Dev Container must resolve `phpbb-mariadb` by container name.

### Expected result

After both containers are connected:

- `phpbb-mariadb` is reachable from Discourse;
- the importer can connect using the hostname defined in `surfrepotes.yml`;
- the import can start normally.

---

## 8. Validation checklist

After the import, verify at least the following:

- total user count;
- total category count;
- total topic count;
- total post count;
- private message behavior;
- poll behavior;
- username mapping;
- timestamps;
- browser rendering;
- internal links;
- optional attachments and media if enabled.

For a realistic test, inspect several sample topics and several user profiles.

---

## 9. What is obsolete now

The following are legacy and should not be used as the main migration path anymore:

- rebuilding the phpBB forum locally via XAMPP;
- simulating the forum from a full FTP clone as the central workflow;
- export → convert → import JSON/NDJSON pipelines as the primary strategy;
- custom API-based import scripts as the main migration method.

These references may still appear in historical documents, but they are no longer the active migration model.

---

## 10. Practical quick start

### On Windows

Run:

```bat
lancer_discourse.bat
```

### In VS Code

- reopen the project in the Dev Container;
- run `./setup-devcontainer.sh` if needed;
- verify the MariaDB host resolves;
- run `./run-surfrepotes.sh`.

### In the browser

Open:

```text
http://localhost:3000
```

and inspect the imported forum.

---

## 11. Summary

Current migration flow:

1. start Docker Desktop;
2. verify the SQL dump;
3. restore or reuse MariaDB;
4. connect MariaDB and Discourse to `phpbb_import`;
5. open the Discourse repository in the Dev Container;
6. install dependencies if needed;
7. run the import with `run-surfrepotes.sh`;
8. validate the imported forum;
9. optionally enable files/media later.
