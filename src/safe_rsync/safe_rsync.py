#!/usr/bin/env python3
"""safe_rsync.py — a colourful rsync wrapper for macOS / Linux (requires rsync ≥ 3.2).

Features:
- Wrapper around `rsync` with built-in safety features
- Automatic backups of overwritten/deleted files
- Color-coded CLI output
- Dry-run mode
- Log file summary
"""

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
CYAN = "\033[1;36m"  # bright/bold cyan
RED = "\033[1;31m"  # bright/bold red
ORANGE = "\033[1;33m"  # bright/bold orange
RESET = "\033[0m"  # reset style/colour


def colorprint(color: str, msg: str, **kwargs) -> None:
    """Print a message in the specified ANSI color and reset the style afterwards.

    Args:
        color: ANSI color code.
        msg: The message to print.
        **kwargs: Extra keyword arguments passed to `print()`, such as `end` or `flush`.
    """
    print(f"{color}{msg}{RESET}", **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Platform / rsync guards
# ──────────────────────────────────────────────────────────────────────────────

def abort(msg: str, code: int = 1) -> NoReturn:
    """Print an error message in red and exit the script with the given code."""
    colorprint(RED, f"❌ {msg}")
    sys.exit(code)


def check_platform() -> None:
    """Ensure the script is not run on unsupported platforms like Windows."""
    if platform.system() == "Windows":
        abort("This script supports only macOS and Linux.")


def parse_rsync_version(output: str) -> Tuple[str, Tuple[int, int, int]]:
    """Parse the rsync version from `rsync --version` output.

    Args:
        output: The stdout string from the `rsync --version` command.

    Returns:
        A tuple: (version string, (major, minor, patch) tuple).
    """
    match = re.search(r"rsync\s+version\s+([0-9]+(?:\.[0-9]+)+)", output)
    if not match:
        raise RuntimeError("Couldn't detect rsync version.")

    version_str = match.group(1)
    parts = tuple(int(p) for p in version_str.split("."))
    while len(parts) < 3:
        parts += (0,)
    return version_str, parts  # type: ignore[misc]


def check_rsync(min_version: Tuple[int, int, int] = (3, 2, 0)) -> None:
    """Check if rsync is installed and its version meets the minimum required.

    Args:
        min_version: Minimum required version of rsync.
    """
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
    """Expand `~` and make a path absolute."""
    return os.path.abspath(os.path.expanduser(p))


def build_rsync_command(src: str, dst: str, backup_dir: str, exclude_pattern: str, dry_run: bool) -> list[str]:
    """Construct the full rsync command line.

    Args:
        src: Source directory.
        dst: Destination directory.
        backup_dir: Path for backup of deleted/replaced files.
        exclude_pattern: Files or directories to exclude.
        dry_run: Whether to perform a dry-run.

    Returns:
        A list of arguments for subprocess to run rsync.
    """
    opts: list[str] = [
        "-ah",
        "--delete",
        "--info=stats2,progress2",
        f"--exclude={exclude_pattern}",
        "--backup",
        f"--backup-dir={backup_dir}",
    ]
    if dry_run:
        opts.insert(0, "--dry-run")

    src_with_slash = src.rstrip(os.sep) + os.sep
    return ["rsync", *opts, src_with_slash, dst]


def print_rsync_header(dry_run: bool, exclude_pattern: str, log_file: str, cmd: str) -> None:
    """Print an overview of the upcoming rsync operation.

    Args:
        dry_run: Whether this is a dry run.
        exclude_pattern: Pattern used for exclusions.
        log_file: Path where the log will be saved.
        cmd: The rsync command (list of args).
    """
    colorprint(CYAN, "🚀 Running rsync…")
    if dry_run:
        colorprint(ORANGE, "   🔍 Dry run   : True (no changes will be made)")
    print(f"📦 Excluding:  {exclude_pattern}")
    print(f"📝 Log file:   {log_file}")
    print("🛠 Command:    ")
    for arg in cmd:
        print(f"       {arg}")
    print("────────────────────────────────────────\n")


# ──────────────────────────────────────────────────────────────────────────────
# Core execution
# ──────────────────────────────────────────────────────────────────────────────

def execute_rsync(cmd: list[str]) -> list[str]:
    """Execute the rsync process and collect its summary statistics.

    Args:
        cmd: The full rsync command as a list of strings.

    Returns:
        A list of strings containing rsync summary lines.
    """
    stats: list[str] = []
    prev_len = 0

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

        print()
        proc.wait()

        if proc.returncode != 0:
            abort(f"rsync exited with code {proc.returncode}.", proc.returncode)

    return stats


def save_summary(timestamp: str, stats: list[str], path: str, duration: float) -> None:
    """Save the rsync summary to a log file.

    Args:
        timestamp: When the operation started.
        stats: Summary lines collected from rsync.
        path: File path where the summary should be saved.
        duration: Time taken for the rsync run.
    """
    with open(path, "w") as fh:
        fh.write(f"Rsync summary for {timestamp}\n")
        fh.write("\n────────────────────────────────────────\n")
        fh.write("\n".join(stats))
        fh.write("\n────────────────────────────────────────\n")
        fh.write(f"\nDuration: {duration:.2f} seconds\n")


def print_summary(stats: list[str], duration: float) -> None:
    """Print a color-coded summary of the rsync output to stdout.

    Args:
        stats: Summary lines from rsync.
        duration: Duration of the operation in seconds.
    """
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
    """Orchestrate the full rsync operation, including logs and backup.

    Args:
        src: Source directory.
        dst: Destination directory.
        backup_dir: Directory where backup and logs will be stored.
        dry_run: Whether to perform a dry run or a real sync.
    """
    if not dry_run:
        os.makedirs(backup_dir, exist_ok=True)

    exclude_pattern = "000_rsync_backup_*"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(backup_dir, f"000_rsync_log_{timestamp}.log")

    cmd = build_rsync_command(src, dst, backup_dir, exclude_pattern, dry_run)
    print_rsync_header(dry_run, exclude_pattern, log_file, cmd)

    start = time.time()
    stats = execute_rsync(cmd)
    duration = time.time() - start

    if not dry_run:
        save_summary(timestamp, stats, log_file, duration)

    print_summary(stats, duration)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Parse CLI arguments and execute the rsync wrapper."""
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

    dry_run = args.dry_run
    src = abspath(args.src)
    dst = abspath(args.dst)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(dst, f"000_rsync_backup_{timestamp}")

    if not os.path.isdir(src):
        abort(f"Source does not exist: {src}")

    check_rsync()
    run_rsync(src, dst, backup_dir, dry_run)

    print("────────────────────────────────────────")
    colorprint(GREEN, "\n✅ Rsync complete.")
    print("────────────────────────────────────────")
    colorprint(CYAN, f"📁 Source:             {src}")
    colorprint(CYAN, f"📂 Destination:        {dst}")
    if dry_run:
        colorprint(ORANGE, f"🔍 Dry run:            True (nothing has been changed)")
    else:
        colorprint(CYAN, f"💾 Backup incl. Log:   {backup_dir}")
    print("────────────────────────────────────────" + RESET)


if __name__ == "__main__":
    main()
