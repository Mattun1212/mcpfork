#!/usr/bin/env python3
"""
Idempotently apply fork-specific patches to upstream files.

Patch types
-----------
insert  (default)
    Inserts ``patch`` lines immediately AFTER the first occurrence of
    ``anchor``.  Guarded by ``marker`` — skipped if already present.

replace
    Replaces the text between ``anchor_start`` and ``anchor_end``
    (both inclusive) with ``replacement``.  Guarded by ``marker`` —
    skipped if already present in the file.

All patches are safe to run multiple times (idempotent).

Usage:
    python scripts/apply-fork-patches.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MAIN_PY = REPO_ROOT / "src/mcp_atlassian/servers/main.py"
ATTACHMENTS_PY = REPO_ROOT / "src/mcp_atlassian/confluence/attachments.py"

# ---------------------------------------------------------------------------
# Patch definitions
# ---------------------------------------------------------------------------
PATCHES: list[dict] = [
    # ── servers/main.py: startup Jira token validation ──────────────────────
    {
        "file": MAIN_PY,
        "marker": "# [fork] Validate token is actually reachable at startup",
        "anchor": "                logger.info(\n"
        '                    "Jira configuration loaded and authentication is configured."\n'
        "                )\n",
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
    # ── servers/main.py: startup Confluence token validation ────────────────
    {
        "file": MAIN_PY,
        "marker": "# [fork] Validate token is actually reachable at startup",
        "anchor": "                logger.info(\n"
        '                    "Confluence configuration loaded and authentication is configured."\n'
        "                )\n",
        "patch": (
            "                # [fork] Validate token is actually reachable at startup\n"
            "                try:\n"
            "                    from mcp_atlassian.confluence.client import (\n"
            "                        ConfluenceClient as _ConfluenceClient,\n"
            "                    )\n"
            "\n"
            "                    _ConfluenceClient(\n"
            "                        config=confluence_config\n"
            "                    )._validate_authentication()\n"
            "                except Exception as _e:\n"
            "                    logger.error(\n"
            '                        "Confluence token validation failed at startup — "\n'
            '                        "check that CONFLUENCE_PERSONAL_TOKEN is correct and not expired: %s",\n'
            "                        _e,\n"
            "                    )\n"
            "                # [/fork]\n"
        ),
    },
    # ── confluence/attachments.py: fix _upload_attachment_direct ────────────
    # Upstream uses PUT + "nocheck" which fails on Confluence Server/DC with a
    # 403 CSRF error.  This fork uses POST (matching atlassian-python-api) and
    # the correct "no-check" token value.
    {
        "type": "replace",
        "file": ATTACHMENTS_PY,
        "marker": "# [fork] _upload_attachment_direct: POST + no-check for DC compatibility",
        "anchor_start": "    def _upload_attachment_direct(\n",
        "anchor_end": "    def delete_attachment(",
        "replacement": (
            "    def _upload_attachment_direct(\n"
            "        self,\n"
            "        content_id: str,\n"
            "        file_path: str,\n"
            "        filename: str,\n"
            "        comment: str | None,\n"
            "        minor_edit: bool,\n"
            "    ) -> dict[str, Any] | None:\n"
            '        """\n'
            "        Upload attachment using direct REST API call.\n"
            "\n"
            "        # [fork] _upload_attachment_direct: POST + no-check for DC compatibility\n"
            "        Uses POST for both new and existing attachments, matching the\n"
            "        atlassian-python-api behaviour:\n"
            "          - New attachment:  POST /rest/api/content/{id}/child/attachment\n"
            "          - Update existing: POST /rest/api/content/{id}/child/attachment/{att_id}/data\n"
            "\n"
            "        Upstream uses PUT + ``X-Atlassian-Token: nocheck`` which causes 403\n"
            "        CSRF errors on Confluence Server/Data Center.\n"
            "        # [/fork]\n"
            "\n"
            "        Args:\n"
            "            content_id: The Confluence content ID\n"
            "            file_path: Full path to the file\n"
            "            filename: Name of the file\n"
            "            comment: Optional comment for the attachment\n"
            "            minor_edit: Whether this is a minor edit\n"
            "\n"
            "        Returns:\n"
            "            Attachment metadata dict if successful, None otherwise\n"
            '        """\n'
            "        file_handle = None\n"
            "        try:\n"
            '            base_url = self.config.url.rstrip("/")\n'
            '            base_path = f"rest/api/content/{content_id}/child/attachment"\n'
            "\n"
            '            # X-Atlassian-Token must be "no-check" (with hyphen) — Confluence Server/DC\n'
            '            # rejects "nocheck" (without hyphen) with a 403 CSRF error.\n'
            "            headers = {\n"
            '                "X-Atlassian-Token": "no-check",\n'
            '                "Accept": "application/json",\n'
            "            }\n"
            "\n"
            "            # Check if an attachment with this filename already exists so we can\n"
            "            # route to the correct endpoint (same logic as atlassian-python-api).\n"
            "            existing_id: str | None = None\n"
            "            try:\n"
            "                check_resp = self.confluence._session.get(\n"
            '                    f"{base_url}/{base_path}",\n'
            "                    headers=headers,\n"
            '                    params={"filename": filename},\n'
            "                )\n"
            "                if check_resp.status_code == 200:\n"
            "                    check_data = check_resp.json()\n"
            '                    results = check_data.get("results", [])\n'
            "                    if results:\n"
            '                        existing_id = results[0].get("id")\n'
            "            except Exception as check_err:\n"
            '                logger.debug(f"Could not check existing attachment: {check_err}")\n'
            "\n"
            "            upload_url = (\n"
            '                f"{base_url}/{base_path}/{existing_id}/data"\n'
            "                if existing_id\n"
            '                else f"{base_url}/{base_path}"\n'
            "            )\n"
            "\n"
            '            file_handle = open(file_path, "rb")  # noqa: SIM115\n'
            '            files: dict[str, Any] = {"file": (filename, file_handle)}\n'
            "            if comment:\n"
            '                files["comment"] = (None, comment, "text/plain; charset=utf-8")\n'
            "\n"
            "            data: dict[str, str] = {}\n"
            "            if minor_edit is not None:\n"
            '                data["minorEdit"] = str(minor_edit).lower()\n'
            "\n"
            "            response = self.confluence._session.post(\n"
            "                upload_url, headers=headers, files=files, data=data\n"
            "            )\n"
            "            response.raise_for_status()\n"
            "\n"
            "            result = response.json()\n"
            '            if isinstance(result, dict) and "results" in result:\n'
            '                results_list = result.get("results", [])\n'
            "                return results_list[0] if results_list else result\n"
            "            return result\n"
            "\n"
            "        except Exception as e:\n"
            '            logger.error(f"Direct API upload failed: {e}")\n'
            "            return None\n"
            "        finally:\n"
            "            if file_handle is not None:\n"
            "                file_handle.close()\n"
            "\n"
            "    def delete_attachment("
        ),
    },
]


# ---------------------------------------------------------------------------
# Patch engine
# ---------------------------------------------------------------------------


def _apply_insert(patch: dict) -> bool:
    """Insert lines after ``anchor``. Returns True if applied."""
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


def _apply_replace(patch: dict) -> bool:
    """Replace the text between ``anchor_start`` and ``anchor_end`` (both
    inclusive).  Returns True if applied."""
    path: Path = patch["file"]
    text = path.read_text(encoding="utf-8")

    if patch["marker"] in text:
        print(f"[skip] {path.name}: patch already applied ({patch['marker']!r})")
        return False

    start_anchor: str = patch["anchor_start"]
    end_anchor: str = patch["anchor_end"]

    start_idx = text.find(start_anchor)
    if start_idx == -1:
        print(
            f"[WARN] {path.name}: anchor_start not found — patch skipped.\n"
            f"       anchor_start: {start_anchor!r}",
            file=sys.stderr,
        )
        return False

    end_idx = text.find(end_anchor, start_idx + len(start_anchor))
    if end_idx == -1:
        print(
            f"[WARN] {path.name}: anchor_end not found after anchor_start — patch skipped.\n"
            f"       anchor_end: {end_anchor!r}",
            file=sys.stderr,
        )
        return False

    patched = (
        text[:start_idx] + patch["replacement"] + text[end_idx + len(end_anchor) :]
    )
    path.write_text(patched, encoding="utf-8")
    print(f"[ok]   {path.name}: patch applied ({patch['marker']!r})")
    return True


def apply_patch(patch: dict) -> bool:
    patch_type = patch.get("type", "insert")
    if patch_type == "replace":
        return _apply_replace(patch)
    return _apply_insert(patch)


def main() -> None:
    applied = 0
    for patch in PATCHES:
        if apply_patch(patch):
            applied += 1
    print(f"\nDone — {applied}/{len(PATCHES)} patch(es) applied.")


if __name__ == "__main__":
    main()
