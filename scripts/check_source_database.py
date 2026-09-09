#!/usr/bin/env python3
"""Read-only preflight checks for a phpBB source database."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pymysql


REQUIRED_TABLES = ("users", "forums", "topics", "posts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a phpBB database before import")
    parser.add_argument("--db-host", required=True)
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--db-user", required=True)
    parser.add_argument("--db-password", default=os.environ.get("PHPBB_DB_PASSWORD"))
    parser.add_argument("--table-prefix", default="phpbb_")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.db_password:
        raise SystemExit("Missing database password: set PHPBB_DB_PASSWORD or pass --db-password.")
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.table_prefix):
        raise SystemExit("The table prefix may only contain letters, digits and underscores.")

    connection = pymysql.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=30,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            mysql_version = cursor.fetchone()["version"]
            cursor.execute("SHOW TABLES")
            table_names = {next(iter(row.values())) for row in cursor.fetchall()}
            expected = {f"{args.table_prefix}{name}" for name in REQUIRED_TABLES}
            missing = sorted(expected - table_names)
            if missing:
                raise RuntimeError("Missing required phpBB tables: " + ", ".join(missing))

            counts = {}
            for name in REQUIRED_TABLES:
                cursor.execute(f"SELECT COUNT(*) AS count FROM `{args.table_prefix}{name}`")
                counts[name] = cursor.fetchone()["count"]
            config_table = f"{args.table_prefix}config"
            row = None
            if config_table in table_names:
                cursor.execute(
                    f"SELECT config_value FROM `{config_table}` "
                    "WHERE config_name = 'version' LIMIT 1"
                )
                row = cursor.fetchone()
    finally:
        connection.close()

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "database": {"host": args.db_host, "name": args.db_name, "prefix": args.table_prefix},
        "mysql_version": mysql_version,
        "phpbb_version": row["config_value"] if row else None,
        "counts": counts,
        "status": "ok",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Source database is ready for import.")
    print(json.dumps(report["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
