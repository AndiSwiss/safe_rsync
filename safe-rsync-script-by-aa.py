#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import datetime
import re
from colorama import init, Fore, Style

init(autoreset=True)

# Color shortcuts
CYAN = Fore.CYAN + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
RESET = Style.RESET_ALL

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
    os.makedirs(backup_dir, exist_ok=True)
    src = os.path.join(src, "")  # Ensure trailing slash

    cmd = [
        "rsync", "-a", "--delete", "--backup",
        f"--backup-dir={backup_dir}",
        "--info=progress2", src, dst
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"{CYAN}🚀 Running rsync... (this might take a while)")
    print(f"   🔍 Dry run: {dry_run}")
    print("")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in process.stdout:
            if "%" in line or "to-check" in line:
                print(line.strip())
    except KeyboardInterrupt:
        print(f"\n{RED}⛔ Aborted by user.")
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

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = get_abs(f"../{os.path.basename(args.dst)}_backup_{timestamp}")

    src = get_abs(args.src)
    dst = get_abs(args.dst)

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
    