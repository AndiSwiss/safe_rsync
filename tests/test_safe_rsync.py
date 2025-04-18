# tests/test_safe_rsync.py
"""
Very first smoke‑test for safe_rsync.

Run with:  pytest -q
"""

import re

import safe_rsync as rs

# ────────────────────────────────────────────────────────────────────────
# 1.  Parsing the rsync version string
# ────────────────────────────────────────────────────────────────────────
def test_parse_rsync_version():
    out = "rsync  version  3.2.7  protocol 31\nCopyright (C) 1996-2022"
    ver_str, ver_tuple = rs.parse_rsync_version(out)

    assert ver_str == "3.2.7"
    assert ver_tuple == (3, 2, 7)


# ────────────────────────────────────────────────────────────────────────
# 2.  Building the rsync command
# ────────────────────────────────────────────────────────────────────────
def test_build_rsync_command_basics(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    backup = tmp_path / "backup"
    src.mkdir()
    dst.mkdir()
    backup.mkdir()

    cmd = rs.build_rsync_command(
        src=str(src),
        dst=str(dst),
        backup_dir=str(backup),
        exclude_pattern="000_rsync_backup_*",
        dry_run=True,
    )

    # The command must start with 'rsync --dry-run' …
    assert cmd[:2] == ["rsync", "--dry-run"]

    # …and contain the expected archive/delete switches.
    joined = " ".join(cmd)
    print('cmd:', cmd)
    print('joined', joined)
    for flag in ("-a", "--delete", "--backup", "--info=stats2,progress2"):
        assert re.search(rf"\b{re.escape(flag)}\b", joined)
