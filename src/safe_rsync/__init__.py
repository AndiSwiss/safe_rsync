# src/safe_rsync/__init__.py
"""
safe_rsync – colourful and safe rsync wrapper.

Re‑export the main public API so users can just:
    import safe_rsync as rs
"""

from .safe_rsync import (
    GREEN,
    CYAN,
    RED,
    ORANGE,
    RESET,
    colorprint,
    abort,
    check_platform,
    parse_rsync_version,
    check_rsync,
    abspath,
    build_rsync_command,
    print_rsync_header,
    execute_rsync,
    save_summary,
    print_summary,
    run_rsync,
    main
)
