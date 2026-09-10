# phpBB → Discourse Migration Manual

This document describes the current migration workflow for the Surfrepotes forum, moving from **phpBB 3.0.13-PL1** to **Discourse**.

The legacy approach based on simulating the entire phpBB forum from an FTP clone, XAMPP, and local phpBB rehosting is no longer the primary workflow. The current migration is centered on the **Discourse phpBB importer/plugin**, a restored phpBB database, and a small set of helper scripts.

---

## 1. Goal of the migration

The objective is to migrate the Surfrepotes forum data from phpBB into Discourse with a controlled, repeatable process.

The current workflow is designed to:

- restore the phpBB database locally;
- connect the Discourse importer to that local source;
- run the import in a controlled way;
- validate the imported content;
- optionally handle files and media later.

---

## 2. Required environment

### 2.1 Windows host

The migration workflow starts from a Windows machine because the original SQL dump and helper launchers are stored there.

You should have:

- **Windows 10/11**;
- **Docker Desktop** installed;
- access to **WSL2**;
- **VS Code** installed;
- the **Dev Containers** extension installed.

### 2.2 WSL2 Ubuntu

The main local tooling runs inside **Ubuntu under WSL2**.

This environment is used to:

- run shell scripts;
- interact with Docker;
- compute checksums;
- launch VS Code into the Discourse workspace;
- connect containers to the same Docker network.

Typical WSL path layout:

- Discourse repository: `/home/flore/discourse`
- Windows drive C: mounted under `/mnt/c`

### 2.3 Docker

Docker is required for:

- the local **Discourse** stack;
- the temporary **MariaDB** container used to restore the phpBB dump;
- container networking between Discourse and MariaDB.

### 2.4 Discourse dev container

The Discourse project is opened in a **Dev Container** from VS Code.

That container is where you run:

- the phpBB import command;
- the Ruby bundle setup;
- the import scripts and validation steps.

---

## 3. Migration architecture

The current migration flow is:

```text
Windows SQL dump
    ↓
WSL copy/checksum
    ↓
Temporary MariaDB container
    ↓
Discourse Dev Container
    ↓
phpBB importer/plugin
    ↓
Validation
```

### What this means

- The **SQL dump** is the source of truth.
- MariaDB is only a temporary local staging database.
- Discourse reads from that local MariaDB source through the importer.
- Validation happens after the import.

This avoids rebuilding the old phpBB forum as a full local website.

---

## 4. Scripts and their locations

The migration is supported by a small set of scripts and config files.

### 4.1 Windows launcher

#### `lancer_discourse.bat`
**Location:** repository root

This is the main Windows launcher used to prepare the local migration environment.

What it does:

- starts Docker Desktop;
- verifies the phpBB SQL dump exists;
- computes the dump SHA-256 hash;
- creates or starts the temporary MariaDB container `phpbb-mariadb`;
- imports the SQL dump only when needed;
- prepares the Docker network `phpbb_import`;
- opens the Discourse project in VS Code;
- reminds you to reopen the project in the Dev Container;
- provides the import command to run inside the Dev Container.

This launcher does **not** run the import itself. It prepares the environment.

---

### 4.2 Linux helper script

#### `surfrepotes-migration.sh`
**Location:** repository root

This script is a small WSL helper used to connect containers to the shared Docker network.

What it does:

- ensures the `phpbb_import` Docker network exists;
- verifies the MariaDB container is running;
- detects the Discourse dev container;
- connects both containers to the same network.

This is useful when the Dev Container has been created and the import needs network visibility to the MariaDB source.

---

### 4.3 Import configuration

#### `surfrepotes.yml`
**Location:** repository root

This is the phpBB importer configuration file.

It contains:

- the MariaDB connection information;
- the phpBB table prefix;
- the local Discourse URL;
- import options such as attachments, PMs, polls, avatars, etc.;
- file-location settings for optional media import.

The important settings currently are:

- MariaDB host: `phpbb-mariadb`
- schema: `surfrepotes`
- table prefix: `phpbb3_`
- phpBB base directory: `/workspace/discourse/phpbb_data`
- Discourse URL: `http://localhost:3000`

---

### 4.4 Dev Container setup helper

#### `setup-devcontainer.sh`
**Location:** repository root

This helper installs the system dependencies required inside the Discourse Dev Container.

What it does:

- updates apt packages;
- installs MariaDB development headers;
- installs build tools and pkg-config;
- runs `bundle install`.

This script is meant to be run inside the Dev Container.

---

### 4.5 Import runner

#### `run-surfrepotes.sh`
**Location:** repository root

This is the command that launches the phpBB → Discourse import.

What it does:

- checks that `script/import_scripts/phpbb3/surfrepotes.yml` exists;
- runs the Discourse importer with that YAML file.

The actual import happens here.

---

## 5. Discourse importer files used by the run script

The `run-surfrepotes.sh` helper points to the importer files under the Discourse repository.

### Importer YAML path

```text
script/import_scripts/phpbb3/surfrepotes.yml
```

### Importer Ruby entrypoint

```text
script/import_scripts/phpbb3.rb
```

### Copy of the launcher command inside the Dev Container

```bash
bundle exec ruby script/import_scripts/phpbb3.rb script/import_scripts/phpbb3/surfrepotes.yml
```

This is the actual import command.

---

## 6. The database preparation flow

### Step 1 — Verify the SQL dump

The launcher checks that the dump file exists on Windows:

```text
C:\Users\flore\source\repos\Surfrepotes\Travail\Input\surfrepotes_mysql_db.sql
```

It also references the WSL equivalent:

```text
/mnt/c/Users/flore/source/repos/Surfrepotes/Travail/Input/surfrepotes_mysql_db.sql
```

### Step 2 — Compute checksum

The script computes a SHA-256 hash for the dump.

This is used to avoid reimporting an unchanged dump on every launch.

### Step 3 — Create or start MariaDB

The temporary MariaDB container is named:

```text
phpbb-mariadb
```

It uses:

- root password: `phpbbroot`
- database name: `surfrepotes`

### Step 4 — Import only if needed

If the dump hash has changed, the database is rebuilt and the dump is imported again.

If the hash is the same, the launcher skips reimporting.

---

## 7. Network setup

The Discourse Dev Container and MariaDB container must share the same Docker network.

The shared network name is:

```text
phpbb_import
```

### Why this matters

Discourse runs inside a container, and MariaDB runs inside another container.
Without a shared Docker network, the importer cannot resolve `phpbb-mariadb` by name.

### Expected connection flow

- MariaDB container joins `phpbb_import`
- Discourse dev container joins `phpbb_import`
- the importer resolves `phpbb-mariadb` via Docker DNS

---

## 8. Dev Container workflow

After `lancer_discourse.bat` prepares the environment:

1. Open the project in VS Code.
2. Reopen it in the Dev Container.
3. Run the dependency setup if needed:

```bash
./setup-devcontainer.sh
```

4. Verify network visibility:

```bash
getent hosts phpbb-mariadb
```

5. Run the import:

```bash
./run-surfrepotes.sh
```

or directly:

```bash
bundle exec ruby script/import_scripts/phpbb3.rb script/import_scripts/phpbb3/surfrepotes.yml
```

6. Open Discourse:

```text
http://localhost:3000
```

---

## 9. Import configuration details

### Database section

The importer connects to the temporary MariaDB instance using:

- host: `phpbb-mariadb`
- port: `3306`
- username: `root`
- password: `phpbbroot`
- schema: `surfrepotes`
- prefix: `phpbb3_`

### Import section

The configuration currently enables:

- `private_messages: true`
- `polls: true`

The configuration currently disables:

- `attachments: false`
- `avatars.uploaded: false`
- `avatars.gallery: false`
- `avatars.remote: false`
- `passwords: false`
- `likes: false`

### Files section

The base directory is set to:

```text
/workspace/discourse/phpbb_data
```

This path is only needed when importing files such as:

- attachments;
- avatars;
- smilies.

---

## 10. Migration phases

### Phase A — Environment preparation

- start Docker Desktop;
- ensure WSL Ubuntu is available;
- open the Discourse project in VS Code;
- create/reuse the MariaDB temporary container;
- connect the containers to `phpbb_import`.

### Phase B — Source database preparation

- verify the SQL dump exists;
- hash the dump;
- import it into MariaDB if it is new or changed.

### Phase C — Discourse import

- reopen the project in the Dev Container;
- install native dependencies if necessary;
- run the importer through `run-surfrepotes.sh` or the direct Ruby command.

### Phase D — Validation

- check the import results in Discourse;
- confirm the main forum objects are present;
- review warnings and skipped records.

### Phase E — Optional media handling

- only if needed, prepare `phpbb_data/files` and `phpbb_data/images`;
- enable attachments and avatar options later.

---

## 11. Validation checklist

After the import, verify at minimum:

- users imported correctly;
- categories imported correctly;
- topics imported correctly;
- posts imported correctly;
- private messages preserved if enabled;
- poll data imported if enabled;
- timestamps look correct;
- internal links resolve sensibly;
- the Discourse forum is accessible in the browser.

---

## 12. What is obsolete now

The following are legacy and should not be treated as the main migration path anymore:

- rebuilding the phpBB forum locally via XAMPP;
- simulating the old forum from an FTP clone as the central workflow;
- export/convert/import JSON pipeline as the primary strategy;
- custom API-based import scripts as the main migration path.

These may still exist as historical context, but they are not the current operating model.

---

## 13. Practical quick start

### On Windows

Run:

```bat
lancer_discourse.bat
```

### Then in VS Code

- reopen in the Dev Container;
- run `./setup-devcontainer.sh` if needed;
- verify `phpbb-mariadb` is reachable;
- run `./run-surfrepotes.sh`.

### Then validate

Open:

```text
http://localhost:3000
```

and inspect the imported forum.

---

## 14. Summary

Current migration flow:

1. start Docker Desktop;
2. verify the SQL dump;
3. restore/update MariaDB if needed;
4. connect MariaDB and Discourse to `phpbb_import`;
5. open the project in the Discourse Dev Container;
6. run the import with `run-surfrepotes.sh`;
7. validate the imported forum in Discourse;
8. handle files/media later if needed.
