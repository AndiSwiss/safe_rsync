#!/usr/bin/env python3
"""safe_rsync.py — a colourful rsync wrapper for macOS / Linux (requires rsync ≥ 3.2)."""

import argparse
import datetime
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import NoReturn, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# ANSI colours
# ──────────────────────────────────────────────────────────────────────────────
GREEN = "\033[1;32m"  # bright/bold green
CYAN = "\033[1;36m"   # bright/bold cyan
RED = "\033[1;31m"    # bright/bold red
RESET = "\033[0m"     # reset style/colour


def colorprint(color: str, msg: str, **kwargs) -> None:  # noqa: N802
    """Print *msg* in *color* and reset the style afterwards.

    Extra keyword arguments are forwarded to :pyfunc:`print` so you can pass
    ``end``/``flush`` if needed.
    """
    print(f"{color}{msg}{RESET}", **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Platform / rsync guards
# ──────────────────────────────────────────────────────────────────────────────

def abort(msg: str, code: int = 1) -> NoReturn:
    colorprint(RED, f"❌ {msg}")
    sys.exit(code)


def check_platform() -> None:
    if platform.system() == "Windows":
        abort("This script supports only macOS and Linux.")


def parse_rsync_version(output: str) -> Tuple[str, Tuple[int, int, int]]:
    """Return the version string and a ``(major, minor, patch)`` tuple."""
    match = re.search(r"rsync\s+version\s+([0-9]+(?:\.[0-9]+)+)", output)
    if not match:
        raise RuntimeError("Couldn't detect rsync version.")

    version_str = match.group(1)
    parts = tuple(int(p) for p in version_str.split("."))
    while len(parts) < 3:
        parts += (0,)
    return version_str, parts  # type: ignore[misc]


def check_rsync(min_version: Tuple[int, int, int] = (3, 2, 0)) -> None:
    """Ensure rsync is present and ≥ *min_version*."""
    if shutil.which("rsync") is None:
        abort("rsync not found in $PATH.")

    output = subprocess.check_output(["rsync", "--version"], text=True)
    version_str, version = parse_rsync_version(output)

    if version < min_version:
        abort(f"rsync ≥ {'.'.join(map(str, min_version))} required, found {version_str}.")

    colorprint(GREEN, f"✅ rsync version {version_str} detected.")


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def abspath(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))


def build_rsync_command(src: str, dst: str, backup_dir: str, exclude_pattern: str, dry_run: bool) -> list[str]:
    """Return the full rsync command list."""
    opts: list[str] = [
        "-a", # archive mode
        "-h", # human-readable
        "--delete", # delete extraneous files from destination dirs
        "--backup", # make backups of files that are replaced or deleted
        f"--backup-dir={backup_dir}", # store backups in this directory
        f"--exclude={exclude_pattern}", # exclude files matching this pattern (e.g., backup dir)
        "--info=stats2,progress2", # show stats and progress
    ]
    if dry_run:
        opts.insert(0, "--dry-run")  # *before* paths

    # ensure a trailing slash so rsync copies the *contents* of *src*
    src_with_slash = src.rstrip(os.sep) + os.sep
    return ["rsync", *opts, src_with_slash, dst]


def print_rsync_header(dry_run: bool, exclude_pattern: str, log_file: str) -> None:
    colorprint(CYAN, "🚀 Running rsync…")
    print(f"   🔍 Dry run   : {dry_run}")
    print(f"   📦 Excluding : {exclude_pattern}")
    print(f"   📝 Log file  : {log_file}\n")


# ──────────────────────────────────────────────────────────────────────────────
# Core execution
# ──────────────────────────────────────────────────────────────────────────────

def execute_rsync(cmd: list[str]) -> list[str]:
    """Run *cmd*, stream progress, return the final stats2 lines."""
    stats: list[str] = []
    prev_len = 0  # length of last progress line (for clean overwrite)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                line = line.rstrip()
                if not line:
                    continue

                if re.match(r"^(Number of|Total|Literal|Matched|File list|sent|total size)", line):
                    stats.append(line)
                elif "%" in line or "to-chk=" in line:
                    padding = " " * max(prev_len - len(line), 0)
                    print(f"\r{line}{padding}", end="", flush=True)
                    prev_len = len(line)
        except KeyboardInterrupt:
            proc.terminate()
            abort("Interrupted by user.")

        print()  # newline after progress
        proc.wait()

        if proc.returncode != 0:
            abort(f"rsync exited with code {proc.returncode}.", proc.returncode)

    return stats


def save_summary(stats: list[str], path: str, duration: float) -> None:
    with open(path, "w") as fh:
        fh.write("\n".join(stats))
        fh.write(f"\nDuration: {duration:.2f} seconds\n")


def print_summary(stats: list[str], duration: float) -> None:
    colorprint(GREEN, "\n✅ Rsync summary:")
    print("────────────────────────────────────────")
    for line in stats:
        colorprint(CYAN, line)
    colorprint(CYAN, f"⏱ Duration: {duration:.2f} seconds")
    print("────────────────────────────────────────")


# ──────────────────────────────────────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────────────────────────────────────

def run_rsync(src: str, dst: str, backup_dir: str, dry_run: bool) -> None:
    os.makedirs(backup_dir, exist_ok=True)
    exclude_pattern = "000_rsync_backup_*"  # works on macOS & Linux

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(backup_dir, f"000_rsync_log_{timestamp}.log")

    cmd = build_rsync_command(src, dst, backup_dir, exclude_pattern, dry_run)
    print_rsync_header(dry_run, exclude_pattern, log_file)

    start = time.time()
    stats = execute_rsync(cmd)
    duration = time.time() - start

    save_summary(stats, log_file, duration)
    print_summary(stats, duration)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    check_platform()

    parser = argparse.ArgumentParser(
        description="Fast & safe rsync wrapper with colourful progress and logs.",
        epilog="Example:\n  ./safe_rsync.py -n ~/data1 ~/data2",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("src", help="Source directory")
    parser.add_argument("dst", help="Destination directory")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Dry run (no changes)")
    args = parser.parse_args()

    src = abspath(args.src)
    dst = abspath(args.dst)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(dst, f"000_rsync_backup_{timestamp}")

    if not os.path.isdir(src):
        abort(f"Source does not exist: {src}")

    check_rsync()
    run_rsync(src, dst, backup_dir, args.dry_run)

    colorprint(GREEN, "\n✅ Rsync complete.")
    print("────────────────────────────────────────")
    colorprint(CYAN, f"📁 Source      : {src}")
    colorprint(CYAN, f"📂 Destination : {dst}")
    colorprint(CYAN, f"💾 Backup dir  : {backup_dir}")
    colorprint(CYAN, f"🔍 Dry run     : {args.dry_run}")
    print("────────────────────────────────────────" + RESET)

if __name__ == "__main__":
    main()

