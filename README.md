# safe_rsync 🛡

A colorful, safe, and scriptable wrapper around `rsync` for macOS and Linux (requires `rsync ≥ 3.2`).

> ✅ Automatically makes backups of files that would be deleted or overwritten  
> 🔍 Includes a dry-run mode  
> 🎨 Outputs colorful progress and summaries  
> 📝 Logs each run with stats and duration  

---

## 🚀 Quick Start

You don't need the whole project for just running the script. You only need the file [src/safe_rsync/safe_rsync.py](src/safe_rsync/safe_rsync.py).
You would need the whole project to further develop or test it.

```bash
python3 src/safe_rsync/safe_rsync.py [OPTIONS] SOURCE DESTINATION
```

### Example

```bash
# Dry run
python3 src/safe_rsync/safe_rsync.py -n ~/Documents ~/Backups

# Actual sync
python3 src/safe_rsync/safe_rsync.py ~/Documents ~/Backups
```

---

## ⚙️ Features

- `--delete` and `--backup` flags enabled for safe syncing
- Files deleted from the destination are saved in a time-stamped backup directory
- `--info=stats2,progress2` for a live rsync progress bar
- Excludes backup folders automatically
- Summary logs stored per run

---

## 🧪 Running Tests

### Run all tests:

```bash
pytest
```

### Only unit tests:

```bash
pytest -m unit
```

### Only integration tests:

```bash
pytest -m integration
```

### Generate coverage report:

```bash
pytest --cov=src --cov-report=term --cov-report=xml
```

---

## 🧰 Project Structure

```
src/
  safe_rsync/           → Main script and package
tests/                  → Unit + integration tests
testdata-manual-testing/ → Manual folders for live testing
pyproject.toml          → Build system / dev config
dev_requirements.txt    → Test/development dependencies
```

---

## 🔧 Requirements

- Python 3.9+
- `rsync` version 3.2 or newer (check with `rsync --version`)
- Works on macOS and Linux (❌ Windows not supported)

Install dev tools:

```bash
pip install -r dev_requirements.txt
```

---

## 📦 Packaging (optional)

To install locally for CLI access:

```bash
pip install -e .
```

Then run with:

```bash
safe_rsync ...
```

---

## 🛠 Manual Testing

You can use the `testdata-manual-testing/` folder to try syncing example directories:

```bash
python3 src/safe_rsync/safe_rsync.py -n "testdata-manual-testing/YOUR_TEST_FOLDER" "testdata-manual-testing/YOUR_BACKUP_FOLDER"
```

---

## 📝 License

MIT License — © 2025 Andreas Ambühl https://andiswiss.ch
