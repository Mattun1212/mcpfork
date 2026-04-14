#!/usr/bin/env python3
"""
Idempotently apply fork-specific patches to upstream files.

Each patch is guarded by  # [fork] ... # [/fork]  markers.
If the markers already exist in the target file the patch is skipped,
so this script is safe to run multiple times (e.g. after every upstream sync).

Usage:
    python scripts/apply-fork-patches.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MAIN_PY = REPO_ROOT / "src/mcp_atlassian/servers/main.py"

# ---------------------------------------------------------------------------
# Patch definitions
# Each entry is a dict with:
#   file       – Path to the file to patch
#   marker     – Unique string that appears in the patch; used to detect
#                whether the patch is already applied.
#   anchor     – Line that must appear in the file; the patch is inserted
#                immediately AFTER the first occurrence of this line.
#   patch      – The lines to insert (already indented, with trailing \n).
# ---------------------------------------------------------------------------
PATCHES: list[dict] = [
    {
        "file": MAIN_PY,
        "marker": "# [fork] Validate token is actually reachable at startup",
        "anchor": '                logger.info(\n'
                  '                    "Jira configuration loaded and authentication is configured."\n'
                  '                )\n',
        "patch": (
            "                # [fork] Validate token is actually reachable at startup\n"
            "                try:\n"
            "                    from mcp_atlassian.jira.client import JiraClient as _JiraClient\n"
            "\n"
            "                    _JiraClient(config=jira_config)._validate_authentication()\n"
            "                except Exception as _e:\n"
            "                    logger.error(\n"
            '                        "Jira token validation failed at startup — "\n'
            '                        "check that JIRA_PERSONAL_TOKEN is correct and not expired: %s",\n'
            "                        _e,\n"
            "                    )\n"
            "                # [/fork]\n"
        ),
    },
    {
        "file": MAIN_PY,
        "marker": "# [fork] Validate token is actually reachable at startup",
        "anchor": '                logger.info(\n'
                  '                    "Confluence configuration loaded and authentication is configured."\n'
                  '                )\n',
        "patch": (
            "                # [fork] Validate token is actually reachable at startup\n"
            "                try:\n"
            "                    from mcp_atlassian.confluence.client import (\n"
            "                        ConfluenceClient as _ConfluenceClient,\n"
            "                    )\n"
            "\n"
            "                    _ConfluenceClient(config=confluence_config)._validate_authentication()\n"
            "                except Exception as _e:\n"
            "                    logger.error(\n"
            '                        "Confluence token validation failed at startup — "\n'
            '                        "check that CONFLUENCE_PERSONAL_TOKEN is correct and not expired: %s",\n'
            "                        _e,\n"
            "                    )\n"
            "                # [/fork]\n"
        ),
    },
]


def apply_patch(patch: dict) -> bool:
    """Apply a single patch. Returns True if the patch was applied, False if already present."""
    path: Path = patch["file"]
    text = path.read_text(encoding="utf-8")

    if patch["marker"] in text:
        print(f"[skip] {path.name}: patch already applied ({patch['marker']!r})")
        return False

    anchor: str = patch["anchor"]
    idx = text.find(anchor)
    if idx == -1:
        print(
            f"[WARN] {path.name}: anchor not found — patch skipped.\n"
            f"       Anchor: {anchor!r}",
            file=sys.stderr,
        )
        return False

    insert_at = idx + len(anchor)
    patched = text[:insert_at] + patch["patch"] + text[insert_at:]
    path.write_text(patched, encoding="utf-8")
    print(f"[ok]   {path.name}: patch applied ({patch['marker']!r})")
    return True


def main() -> None:
    applied = 0
    for patch in PATCHES:
        if apply_patch(patch):
            applied += 1
    print(f"\nDone — {applied}/{len(PATCHES)} patch(es) applied.")


if __name__ == "__main__":
    main()
