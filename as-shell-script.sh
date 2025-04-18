#!/usr/bin/env bash
#
#  safe_rsync.sh – local‑only rsync wrapper for Linux *and* macOS
# ----------------------------------------------------------------------
#  FEATURES
#    • Per‑run backup directory beside <DST>
#    • Timestamped log (stdout+stderr) in the current directory
#    • Optional dry‑run mode (‑n | --dry-run)
#    • Strict error handling (`set -euo pipefail`)
#    • Pretty, locale‑independent summary (may show “Unknown” on non‑English
#      locales)
# ----------------------------------------------------------------------

set -euo pipefail
trap 'echo -e "\n⏹️  Aborted." >&2; exit 130' INT TERM

########################################
# ---------  RUNTIME CHECKS -----------
########################################
# Ensure rsync ≥ 3.1 (need --info=stats2)
if ! RSYNC_VERSION=$(rsync --version 2>/dev/null | grep -oE 'rsync +version +([0-9]+\.[0-9]+(\.[0-9]+)?)' | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?'); then
  echo "❌  rsync not found." >&2
  echo "    On macOS install it via Homebrew:  brew install rsync" >&2
  exit 1
fi

REQUIRED_VERSION="3.1"
if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$RSYNC_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
  echo "❌  rsync >= $REQUIRED_VERSION required (detected $RSYNC_VERSION)." >&2
  echo "    On macOS install it via Homebrew:  brew install rsync" >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "❌  python3 required." >&2; exit 1; }

########################################
# ---------  ARGUMENT PARSING  ---------
########################################
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: safe_rsync.sh [--dry-run|-n] <SRC> <DST>

Synchronises the contents of SRC → DST via rsync, keeps overwritten /
deleted files in a timestamped backup directory, and logs everything.
Remote paths (host:/path or host::module/path) are NOT allowed.

Note: The post‑run log summary relies on rsync’s English “stats2” lines.
On non‑English locales the transferred‑file count/size may read “Unknown”.

Options:
  -n, --dry-run   Perform a trial run with no changes made.
  -h, --help      Show this help text.
EOF
}

while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--dry-run) DRY_RUN=true; shift ;;
    -h|--help)    usage; exit 0 ;;
    -*)           echo "❌ Unknown option: $1" >&2; usage; exit 1 ;;
    *)            break ;;
  esac
done

[[ $# -eq 2 ]] || { echo "❌ Need exactly <SRC> and <DST>." >&2; usage; exit 1; }
SRC=$1
DST=$2

########################################
# --------  REMOTE‑PATH GUARD  ---------
########################################
# Matches rsync's host:/path  OR  host::module/path (optionally with user@)
is_remote() {
  [[ $1 =~ ^([^/@:]+@)?[^/:]+::?.* ]] && [[ $1 != /* ]]
}

if is_remote "$SRC" || is_remote "$DST"; then
  echo "❌  Remote paths are not supported. Provide local directories only." >&2
  exit 1
fi

########################################
# -------  BUILD RUNTIME VALUES  -------
########################################
# Portable nanosecond-ish timestamp via Python3
TIMESTAMP=$(python3 - <<'PY'
import datetime, os
now = datetime.datetime.now()
print(now.strftime(f"%Y-%m-%d_%H-%M-%S_{now.microsecond:06d}") + f"-{os.getpid()}")
PY
)

LOG_FILE="rsync_log_${TIMESTAMP}.log"

# Portable realpath: GNU coreutils or Python3 fallback
if command -v realpath &>/dev/null; then
  LOCAL_DST=$(realpath -m "$DST")
else
  LOCAL_DST=$(python3 - "$DST" <<'PY'
import os, sys; print(os.path.abspath(sys.argv[1]))
PY
  )
fi
BACKUP_DIR="${LOCAL_DST%/}_backup_${TIMESTAMP}"

########################################
# -------------  CHECKS  --------------
########################################
if [[ ! -d $SRC ]]; then
  echo "❌ Source directory '$SRC' does not exist." >&2
  exit 1
fi

if ! $DRY_RUN; then
  [[ -d $DST ]] || { echo "📂 Destination '$DST' missing – creating..."; mkdir -p "$DST"; }
  mkdir -p "$BACKUP_DIR"
fi

########################################
# ---------  BUILD RSYNC CMD  ----------
########################################
RSYNC_OPTS=(
  -a --delete -x                     # stay on same filesystem
  --backup --backup-dir="$BACKUP_DIR"
  --info=stats2,progress2,flist0
  --human-readable
)
$DRY_RUN && RSYNC_OPTS+=(--dry-run)

########################################
# -------------  RUN  -----------------
########################################
echo "🚀  rsync ${RSYNC_OPTS[*]} $SRC/  $DST/"
echo "📁 Backup dir : $BACKUP_DIR"
echo "📝 Log file   : $LOG_FILE"
$DRY_RUN && echo "🔍 Dry‑run    : ON  (no file‑system changes)" || echo "✏️  Dry‑run    : OFF (files will be modified)"
echo "--------------------------------------------"

set +e
rsync "${RSYNC_OPTS[@]}" "$SRC/" "$DST/" 2>&1 | tee "$LOG_FILE"
RSYNC_STATUS=${PIPESTATUS[0]}
set -e

########################################
# -------------  POST  ----------------
########################################
if (( RSYNC_STATUS != 0 )); then
  echo "❌  rsync exited with status $RSYNC_STATUS" >&2
  exit $RSYNC_STATUS
fi

read -r FILES_SENT < <(grep -oE "^Number of regular files transferred: *[0-9]+" "$LOG_FILE" | awk '{print $NF}' | tail -1)
read -r BYTES_SENT < <(grep -oE "^Total transferred file size: *[0-9]+(\.[0-9]+)?[KMGTP]?" "$LOG_FILE" | awk '{for (i=5;i<=NF;++i) printf $i (i==NF?ORS:OFS)}' | tail -1)

echo ""
echo "✅  rsync completed successfully."
echo "--------------------------------------------"
printf "📦 Files transferred : %s\n"  "${FILES_SENT:-Unknown}"
printf "📐 Transferred size  : %s\n"  "${BYTES_SENT:-Unknown}"
printf "📂 Backup location   : %s\n"  "$BACKUP_DIR"
printf "📝 Full log at       : %s\n"  "$LOG_FILE"
printf "🔎 Dry‑run mode      : %s\n"  "$DRY_RUN"
echo "--------------------------------------------"
