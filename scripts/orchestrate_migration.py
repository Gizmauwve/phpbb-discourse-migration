#!/usr/bin/env python3
"""Prepare a complete FTP clone for a Discourse phpBB3 import."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def resolve_forum_path(path: Path) -> Path:
    path = path.expanduser().resolve()
    candidates = (path / "www" / "forum", path / "forum", path)
    for candidate in candidates:
        if (candidate / "store").is_dir() and (candidate / "config.php").is_file():
            return candidate
    raise ValueError("Select the clone root, www/, or the phpBB forum directory.")


def latest_backup(forum_path: Path) -> Path:
    backups = list((forum_path / "store").glob("backup_*.sql.gz")) + list((forum_path / "store").glob("backup_*.sql"))
    if not backups:
        raise FileNotFoundError(f"No phpBB backup_*.sql(.gz) found in {forum_path / 'store'}")
    def key(path: Path) -> tuple[int, float]:
        match = re.match(r"backup_(\d+)_", path.name)
        return (int(match.group(1)) if match else 0, path.stat().st_mtime)
    return max(backups, key=key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a clone for the official Discourse phpBB3 importer")
    parser.add_argument("--clone-path", type=Path, required=True, help="FTP clone root, www/, or forum/")
    parser.add_argument("--source-dump", type=Path, help="Override the backup automatically selected from forum/store")
    parser.add_argument("--original-host", required=True, help="Old host/path without http(s)")
    parser.add_argument("--table-prefix", default="phpbb_")
    parser.add_argument("--output-dir", type=Path, default=Path("data/import/discourse-shared"))
    parser.add_argument("--without-attachments", action="store_true")
    parser.add_argument("--without-private-messages", action="store_true")
    parser.add_argument("--without-polls", action="store_true")
    parser.add_argument("--without-bookmarks", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Run an explicitly supplied command after preparation")
    parser.add_argument("--discourse-command", help="Command that invokes the importer in your Discourse environment")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    forum_path = resolve_forum_path(args.clone_path)
    dump = args.source_dump.resolve() if args.source_dump else latest_backup(forum_path)
    project_root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir if args.output_dir.is_absolute() else project_root / args.output_dir
    state_file = output_dir.parent / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {"started_at": datetime.now(timezone.utc).isoformat(), "forum_path": str(forum_path), "source_dump": str(dump), "stages": {}}
    state["stages"]["select_backup"] = {"status": "success", "backup": str(dump)}
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    command = [sys.executable, "scripts/import_discourse.py", "--source-dump", str(dump),
               "--original-host", args.original_host, "--phpbb-base-dir", str(forum_path),
               "--table-prefix", args.table_prefix, "--output", str(output_dir)]
    for option in ("without_attachments", "without_private_messages", "without_polls", "without_bookmarks"):
        if getattr(args, option):
            command.append("--" + option.replace("_", "-"))
    result = subprocess.run(command, cwd=project_root, text=True, encoding="utf-8", errors="replace", capture_output=True)
    state["stages"]["prepare_import"] = {"status": "success" if result.returncode == 0 else "failed", "output": (result.stdout + result.stderr)[-10000:]}
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result.stdout, end="")
    if result.returncode:
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode
    if not args.execute:
        print("Preparation complete; no server was started and no import has been run.")
        return 0
    if not args.discourse_command:
        print("ERROR: --execute requires --discourse-command.", file=sys.stderr)
        return 2
    imported = subprocess.run(args.discourse_command, cwd=project_root, shell=True)
    state["stages"]["discourse_import"] = {"status": "success" if imported.returncode == 0 else "failed", "returncode": imported.returncode}
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return imported.returncode


if __name__ == "__main__":
    raise SystemExit(main())
