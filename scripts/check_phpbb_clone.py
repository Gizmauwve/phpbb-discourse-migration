#!/usr/bin/env python3
"""Run repeatable static and smoke checks on a local phpBB clone."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tqdm import tqdm


DEPRECATED_PATTERNS = {
    "mysql_* API": re.compile(r"\bmysql_(?:connect|pconnect|query|select_db|fetch_|free_result|error)\s*\(", re.I),
    "short PHP tag": re.compile(r"<\?(?!php|=|xml)", re.I),
    "legacy named constructor": re.compile(
        r"function\s+(?:user|phpbb_seo|seo_meta|template|cache|auth)\s*\(", re.I
    ),
}
ERROR_PATTERNS = re.compile(
    r"Undefined array key|Undefined variable|Parse error|Fatal error|SQL ERROR|"
    r"mysqli_sql_exception|Non-static method|Language file .*couldn't be opened|"
    r"template->_tpl_load_file",
    re.I,
)
REQUIRED_FILES = (
    "index.php",
    "forum/config.php",
    "forum/common.php",
    "forum/language/fr/common.php",
    "forum/styles/prosilver/template/viewtopic_body.html",
    "forum/includes/db/mysqli.php",
)
SKIP_DIRECTORIES = {
    "cache",
    "install",
    "ins_vieux",
}
SKIP_DIRECTORIES_LOWER = {name.lower() for name in SKIP_DIRECTORIES}
# Old phpBB installer/upgrade bundles (install_v3011-3012, install_v309bis, ...)
# are dead code never executed in production; skip any directory named after them.
SKIP_DIRECTORY_PREFIXES_LOWER = ("install_",)
# Windows duplicate files such as "(copie)" are not part of runtime code paths.
SKIP_FILENAME_MARKERS_LOWER = ("(copie)",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Local www directory")
    parser.add_argument("--base-url", help="Optional local URL for HTTP smoke tests")
    parser.add_argument(
        "--php", default="php", help="PHP executable used for syntax checks (default: php)"
    )
    parser.add_argument(
        "--strict-legacy",
        action="store_true",
        help="Treat legacy pattern findings as blocking failures",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Relative URL path to test; may be repeated",
    )
    return parser.parse_args()


def check_required_files(root: Path) -> list[str]:
    return [path for path in REQUIRED_FILES if not (root / path).is_file()]


def check_php_syntax(root: Path, php_executable: str) -> list[str]:
    errors: list[str] = []
    if shutil.which(php_executable) is None and not Path(php_executable).is_file():
        return [f"PHP executable not found: {php_executable}"]

    progress = tqdm(php_files(root), desc="Contrôle syntaxe PHP", unit="fichier")
    for php_file in progress:
        progress.set_postfix_str(str(php_file.relative_to(root))[-50:])
        result = subprocess.run(
            [php_executable, "-l", str(php_file)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip().splitlines()
            detail = output[-1] if output else "syntax check failed"
            errors.append(f"{php_file.relative_to(root)}: {detail}")
    progress.close()
    return errors


def check_legacy_patterns(root: Path) -> list[str]:
    findings: list[str] = []
    progress = tqdm(php_files(root), desc="Recherche de motifs obsolètes", unit="fichier")
    for source_file in progress:
        progress.set_postfix_str(str(source_file.relative_to(root))[-50:])
        try:
            content = source_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(f"{source_file.relative_to(root)}: cannot read file ({exc})")
            continue
        for label, pattern in DEPRECATED_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{source_file.relative_to(root)}: {label}")
    progress.close()
    return findings


def php_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.php")
        if not any(marker in path.name.lower() for marker in SKIP_FILENAME_MARKERS_LOWER)
        if not any(
            part.lower() in SKIP_DIRECTORIES_LOWER
            or part.lower().startswith(SKIP_DIRECTORY_PREFIXES_LOWER)
            for part in path.relative_to(root).parts
        )
    )


def check_http(base_url: str, paths: list[str]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        url = base_url.rstrip("/") + "/" + path.lstrip("/")
        request = Request(url, headers={"User-Agent": "phpbb-clone-check/1.0"})
        try:
            with urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status < 200 or response.status >= 400:
                    findings.append(f"{url}: HTTP {response.status}")
                if ERROR_PATTERNS.search(body):
                    findings.append(f"{url}: known PHP/SQL error found in response")
        except HTTPError as exc:
            findings.append(f"{url}: HTTP {exc.code}")
        except URLError as exc:
            findings.append(f"{url}: unavailable ({exc.reason})")
    return findings


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: clone directory does not exist: {root}", file=sys.stderr)
        return 2

    missing = check_required_files(root)
    syntax_errors = check_php_syntax(root, args.php)
    legacy_findings = check_legacy_patterns(root)
    http_findings = check_http(
        args.base_url,
        args.paths or ["/", "/forum/", "/forum/viewtopic.php?t=10037"],
    ) if args.base_url else []

    sections = (
        ("Missing required files", missing),
        ("PHP syntax errors", syntax_errors),
        ("Legacy PHP patterns", legacy_findings),
        ("HTTP smoke-test findings", http_findings),
    )
    blocking_sections = (
        ("Missing required files", missing),
        ("PHP syntax errors", syntax_errors),
        ("HTTP smoke-test findings", http_findings),
    )
    blocking_total = sum(len(findings) for _, findings in blocking_sections)
    warnings_total = len(legacy_findings)
    strict_legacy_total = warnings_total if args.strict_legacy else 0
    total = blocking_total + strict_legacy_total

    print(f"Checked clone: {root}")
    for title, findings in sections:
        print(f"\n{title}: {len(findings)}")
        for finding in findings:
            print(f"- {finding}")

    if warnings_total and not args.strict_legacy:
        print("\nLegacy findings are warnings only (use --strict-legacy to make them blocking).")
    if args.strict_legacy:
        print("\nStrict legacy mode enabled: legacy findings are blocking.")

    if total == 0:
        result = "PASS" if warnings_total == 0 else "PASS_WITH_WARNINGS"
    else:
        result = "FAIL"
    print(f"\nResult: {result}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
