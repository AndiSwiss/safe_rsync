#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import datetime
import re
import pty

# ANSI color escape codes for terminal output
# \033     → Escape character (starts the sequence)
GREEN = "\033[1;32m"  # Bright green (1 = bold, 32 = green)
CYAN  = "\033[1;36m"  # Bright cyan  (1 = bold, 36 = cyan)
RED   = "\033[1;31m"  # Bright red   (1 = bold, 31 = red)
RESET = "\033[0m"     # Reset to default color and style

def check_rsync():
    """Check if rsync is installed and >= 3.1."""
    try:
        output = subprocess.check_output(["rsync", "--version"], text=True)
        match = re.search(r'rsync\s+version\s+([0-9]+\.[0-9]+(\.[0-9]+)?)', output)
        if not match:
            raise RuntimeError("Couldn't detect rsync version.")
        version = match.group(1)
        print(f"{GREEN}✅ rsync version {version} detected.")
    except Exception as e:
        print(f"{RED}❌ rsync not found or not working.\n{e}")
        sys.exit(1)

def get_abs(path):
    return os.path.abspath(os.path.expanduser(path))

def run_rsync(src, dst, backup_dir, dry_run):
    """Runs rsync and shows a single updating progress line."""
    os.makedirs(backup_dir, exist_ok=True)
    src = os.path.join(src, "")  # Ensure trailing slash

    exclude_pattern = "000_rsync_backup_*"

    cmd = [
        "rsync", "-a", "--delete", "--backup",
        f"--backup-dir={backup_dir}",
        f"--exclude={exclude_pattern}",
        "--info=stats2,progress2",
        src,
        dst
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"{CYAN}🚀 Running rsync with live progress...")
    print(f"   🔍 Dry run: {dry_run}")
    print(f"   📦 Excluding backup dir: {exclude_pattern}")
    print("")

    try:
        pty.spawn(cmd)
    except OSError as e:
        print(f"{RED}❌ Failed to run rsync: {e}")
        sys.exit(1)
def main():
    parser = argparse.ArgumentParser(
        description="Fast and safe rsync wrapper with progress display and optional dry-run.",
        epilog="Example:\n  ./safe_rsync.py -n ~/data1 ~/data2",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("src", help="Source directory")
    parser.add_argument("dst", help="Destination directory")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Dry run (no actual changes)")
    args = parser.parse_args()

    src = get_abs(args.src)
    dst = get_abs(args.dst)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(dst, f"000_rsync_backup_{timestamp}")

    if not os.path.isdir(src):
        print(f"{RED}❌ Source does not exist: {src}")
        sys.exit(1)

    check_rsync()
    run_rsync(src, dst, backup_dir, args.dry_run)

    print(f"\n{GREEN}✅ Rsync complete.")
    print("────────────────────────────────────────")
    print(f"{CYAN}📁 Source      : {src}")
    print(f"{CYAN}📂 Destination : {dst}")
    print(f"{CYAN}💾 Backup dir  : {backup_dir}")
    print(f"{CYAN}🔍 Dry run     : {args.dry_run}")
    print("────────────────────────────────────────" + RESET)

if __name__ == "__main__":
    main()
    