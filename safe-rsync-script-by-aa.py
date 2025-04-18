#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import shutil
import datetime
import re

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("❌ Please install 'colorama' first (used for colored output):")
    print("   pip install colorama")
    sys.exit(1)

# Colored output shortcuts
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
RESET = Style.RESET_ALL

def check_rsync_version(required_version="3.1"):
    """Checks if rsync is installed and meets the minimum required version."""
    try:
        output = subprocess.check_output(["rsync", "--version"], text=True)
        match = re.search(r'rsync\s+version\s+([0-9]+\.[0-9]+(\.[0-9]+)?)', output)
        if not match:
            raise RuntimeError("Couldn't parse rsync version")
        version = match.group(1)
        if tuple(map(int, version.split("."))) < tuple(map(int, required_version.split("."))):
            print(f"{RED}❌ rsync >= {required_version} required (detected {version}).")
            sys.exit(1)
        print(f"{GREEN}✅ rsync version {version} detected.")
    except FileNotFoundError:
        print(f"{RED}❌ rsync not found. Install it (e.g., on macOS: `brew install rsync`)")
        sys.exit(1)

def get_abs_path(path):
    """Returns an absolute path for any input."""
    return os.path.abspath(os.path.expanduser(path))

def run_rsync(src, dst, backup_dir, log_file, dry_run):
    """Runs the rsync command with backup, logging, and optional dry-run."""
    os.makedirs(backup_dir, exist_ok=True)
    src = os.path.join(src, '')  # Ensure trailing slash

    cmd = [
        "rsync", "-av", "--delete", "--backup",
        f"--backup-dir={backup_dir}",
        "--progress", src, dst
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"{CYAN}🚀 Running rsync...")
    print("   " + " ".join(cmd))

    with open(log_file, "w") as log:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="")
            log.write(line)

    print(f"{YELLOW}📝 Log written to: {log_file}")

def parse_rsync_log(log_file):
    """Parses rsync log to extract file transfer summary."""
    summary = {
        "files_transferred": "Unknown",
        "transferred_size": "Unknown"
    }
    with open(log_file) as f:
        for line in f:
            if "Number of regular files transferred" in line:
                summary["files_transferred"] = line.split(":")[-1].strip()
            elif "Total transferred file size" in line:
                summary["transferred_size"] = line.split(":")[-1].strip()
    return summary

def main():
    # Define command-line arguments
    parser = argparse.ArgumentParser(
        description="Safe rsync wrapper with backup, logging, dry-run and summary.",
        epilog="Example:\n  ./safe_rsync.py -n ~/data1 ~/data2",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("src", help="Source directory to sync from")
    parser.add_argument("dst", help="Destination directory to sync to")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Run as a dry run (no changes made)")
    args = parser.parse_args()

    # Format timestamped backup and log file paths
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = get_abs_path(f"../{os.path.basename(args.dst)}_backup_{timestamp}")
    log_file = f"rsync_log_{timestamp}.log"

    # Resolve absolute paths
    src = get_abs_path(args.src)
    dst = get_abs_path(args.dst)

    # Check if source directory exists
    if not os.path.isdir(src):
        print(f"{RED}❌ Source directory does not exist: {src}")
        sys.exit(1)

    # Ensure rsync is present and usable
    check_rsync_version()

    # Run the rsync command
    run_rsync(src, dst, backup_dir, log_file, dry_run=args.dry_run)

    # Summarize results
    summary = parse_rsync_log(log_file)
    print("\n" + GREEN + "✅ Rsync Summary")
    print("────────────────────────────────────────")
    print(f"{CYAN}📁 Source              : {src}")
    print(f"{CYAN}📂 Destination         : {dst}")
    print(f"{CYAN}💾 Backup dir          : {backup_dir}")
    print(f"{CYAN}📝 Log file            : {log_file}")
    print(f"{CYAN}🔎 Dry run mode        : {args.dry_run}")
    print(f"{CYAN}📦 Files transferred   : {summary['files_transferred']}")
    print(f"{CYAN}📐 Transferred size    : {summary['transferred_size']}")
    print("────────────────────────────────────────" + RESET)

if __name__ == "__main__":
    main()
    