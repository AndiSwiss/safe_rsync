# src/safe_rsync/__init__.py
"""
safe_rsync – colourful and safe rsync wrapper.

Re‑export the main public API so users can just:
    import safe_rsync as rs
"""

from .safe_rsync import (      # noqa: F401
    main,
    run_rsync,
    build_rsync_command,
    parse_rsync_version,
    check_rsync,
    colorprint,
    GREEN,
    CYAN,
    RED,
    RESET,
)

__all__ = [
    # functions
    "main",
    "run_rsync",
    "build_rsync_command",
    "parse_rsync_version",
    "check_rsync",
    "colorprint",
    # constants
    "GREEN",
    "CYAN",
    "RED",
    "RESET",
]
