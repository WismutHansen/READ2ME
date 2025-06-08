#!/usr/bin/env python3
"""
bump_version.py – semantic version bump script.

Usage:
    python bump_version.py [major|minor|patch]
    python bump_version.py --set X.Y.Z
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# ---------- config ----------
PYPROJECT_PATH = pathlib.Path("pyproject.toml")
FILES_TO_UPDATE = [
    pathlib.Path("pyproject.toml"),
    pathlib.Path("main.py"),
]
VERSION_REGEX = re.compile(r"\b(\d+)\.(\d+)\.(\d+)\b")
# ----------------------------


def _read_pyproject_version() -> str:
    """Return the version declared in pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        sys.exit("pyproject.toml not found")

    # Prefer tomllib (3.11+) for safety.
    try:
        import tomllib  # type: ignore

        data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        return data["project"]["version"]
    except ModuleNotFoundError:
        # plain regex fallback
        m = re.search(
            r'^version\s*=\s*"(.*?)"', PYPROJECT_PATH.read_text(encoding="utf-8"), re.M
        )
        if not m:
            sys.exit("Version line not found in pyproject.toml")
        return m.group(1)


def _next_version(current: str, part: str) -> str:
    major, minor, patch = map(int, current.split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        sys.exit(f"Unknown part '{part}' (choose major|minor|patch)")
    return f"{major}.{minor}.{patch}"


def _update_file(path: pathlib.Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    replaced, n = VERSION_REGEX.subn(
        lambda m: new if m.group(0) == old else m.group(0), text
    )
    if n:
        path.write_text(replaced, encoding="utf-8")
        print(f"✓ {path} – {n} occurrence{'s' if n != 1 else ''} updated")
    else:
        print(f"• {path} – no version string found (skipped)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump project version (SemVer).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "part",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Which SemVer part to increment",
    )
    group.add_argument(
        "--set", metavar="X.Y.Z", help="Explicitly set version to this value"
    )
    args = parser.parse_args()

    current = _read_pyproject_version()

    new_version = args.set or _next_version(current, args.part)
    if not VERSION_REGEX.fullmatch(new_version):
        sys.exit(f"Invalid version '{new_version}'")

    if new_version == current:
        sys.exit("New version is identical to current; nothing to do.")

    print(f"{current}  →  {new_version}")

    for fp in FILES_TO_UPDATE:
        _update_file(fp, current, new_version)

    print("All done ✨")


if __name__ == "__main__":
    main()
