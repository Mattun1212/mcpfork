#!/usr/bin/env python3
"""Sync main dependencies from upstream sooperset/mcp-atlassian.

Usage:
    python scripts/sync_upstream_deps.py

Exit codes:
    0 - no changes (already up to date)
    1 - pyproject.toml was updated
    2 - error
"""

import re
import sys
import urllib.error
import urllib.request

UPSTREAM_URL = "https://raw.githubusercontent.com/sooperset/mcp-atlassian/main/pyproject.toml"
PYPROJECT_PATH = "pyproject.toml"

# Pattern that matches the full `dependencies = [ ... ]` block (multiline)
DEPS_PATTERN = re.compile(r"(^dependencies\s*=\s*\[)(.*?)(^\])", re.MULTILINE | re.DOTALL)


def fetch_upstream() -> str:
    try:
        with urllib.request.urlopen(UPSTREAM_URL, timeout=30) as resp:
            return resp.read().decode()
    except urllib.error.URLError as e:
        print(f"ERROR: Could not fetch upstream pyproject.toml: {e}", file=sys.stderr)
        sys.exit(2)


def extract_deps_block(content: str) -> str:
    match = DEPS_PATTERN.search(content)
    if not match:
        print("ERROR: Could not find 'dependencies = [...]' block", file=sys.stderr)
        sys.exit(2)
    return match.group(0)


def main() -> int:
    upstream_content = fetch_upstream()
    upstream_deps = extract_deps_block(upstream_content)

    with open(PYPROJECT_PATH, encoding="utf-8") as f:
        fork_content = f.read()

    fork_deps = extract_deps_block(fork_content)

    if fork_deps == upstream_deps:
        print("Dependencies already up to date.")
        return 0

    new_content = DEPS_PATTERN.sub(upstream_deps, fork_content, count=1)

    with open(PYPROJECT_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Show diff summary
    fork_lines = set(fork_deps.splitlines())
    upstream_lines = set(upstream_deps.splitlines())
    added = sorted(upstream_lines - fork_lines)
    removed = sorted(fork_lines - upstream_lines)
    if removed:
        print("Removed:")
        for line in removed:
            print(f"  - {line.strip()}")
    if added:
        print("Added:")
        for line in added:
            print(f"  + {line.strip()}")

    print("\npyproject.toml updated with upstream dependencies.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
