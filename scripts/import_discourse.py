#!/usr/bin/env python3
"""Prepare a phpBB SQL backup for Discourse's official phpBB3 importer."""

from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a phpBB backup for the Discourse importer")
    parser.add_argument("--source-dump", type=Path, required=True, help="phpBB .sql or .sql.gz backup")
    parser.add_argument("--original-host", required=True, help="Old host/path without http(s)")
    parser.add_argument("--phpbb-base-dir", type=Path, help="Clone forum directory for files, images and avatars")
    parser.add_argument("--table-prefix", default="phpbb_")
    parser.add_argument("--output", type=Path, default=Path("data/import/discourse-shared"))
    parser.add_argument("--without-attachments", action="store_true")
    parser.add_argument("--without-private-messages", action="store_true")
    parser.add_argument("--without-polls", action="store_true")
    parser.add_argument("--without-bookmarks", action="store_true")
    return parser.parse_args()


def copy_dump(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Backup not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".gz":
        with gzip.open(source, "rb") as input_file, destination.open("wb") as output_file:
            shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
    elif source.suffix.lower() == ".sql":
        shutil.copy2(source, destination)
    else:
        raise ValueError("The backup must be a .sql or .sql.gz file.")


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    data_dir = output / "data"
    sql_file = data_dir / "phpbb_mysql.sql"
    copy_dump(args.source_dump, sql_file)
    settings = {
        "database": {
            "type": "MySQL", "host": "localhost", "port": 3306,
            "username": "root", "password": "password", "schema": "phpbb",
            "table_prefix": args.table_prefix, "batch_size": 1000,
        },
        "import": {
            "site_name": None, "new_categories": [], "category_mappings": [],
            "tag_mappings": {}, "rank_mapping": {}, "use_bbcode_to_md": False,
            "phpbb_base_dir": "/shared/import/data/phpbb" if args.phpbb_base_dir else None,
            "site_prefix": {"original": args.original_host}, "passwords": False,
            "bookmarks": not args.without_bookmarks,
            "attachments": not args.without_attachments,
            "private_messages": not args.without_private_messages,
            "polls": not args.without_polls, "likes": False,
            "username_as_name": False, "emojis": {}, "custom_fields": [],
        },
    }
    (output / "settings.yml").write_text(yaml.safe_dump(settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.phpbb_base_dir:
        target_clone = data_dir / "phpbb"
        for directory in ("files", "images"):
            source_directory = args.phpbb_base_dir / directory
            if source_directory.is_dir():
                shutil.copytree(source_directory, target_clone / directory, dirs_exist_ok=True)
    print(f"Discourse import files prepared in: {output}")
    print(f"SQL backup: {sql_file}")
    print("Use Discourse Docker's phpbb3 import template; it loads phpbb_mysql.sql into a temporary MySQL database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
