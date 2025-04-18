import subprocess
from datetime import datetime
from pathlib import Path

import pytest
import safe_rsync as rs


# ─────────────────────────────────────────────────────────────────────
# Shared fixture for CLI tests
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def script_path():
    """Returns the absolute path to the CLI entry script safe_rsync.py."""
    path = (Path(__file__).parent.parent / "src" / "safe_rsync" / "safe_rsync.py").resolve()
    assert path.exists(), f"Script not found: {path}"
    return path


@pytest.mark.integration
class TestIntegration:
    def test_rsync_integration_copy(self, tmp_path):
        src = tmp_path / "source"
        dst = tmp_path / "destination"
        src.mkdir()
        dst.mkdir()

        (src / "file1.txt").write_text("Hello world")
        (src / "file2.log").write_text("Log content")
        (src / "subdir").mkdir()
        (src / "subdir" / "nested.txt").write_text("Nested content")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = dst / f"000_rsync_backup_{timestamp}"

        rs.run_rsync(str(src), str(dst), str(backup_dir), dry_run=False)

        assert (dst / "file1.txt").read_text() == "Hello world"
        assert (dst / "file2.log").read_text() == "Log content"
        assert (dst / "subdir" / "nested.txt").read_text() == "Nested content"

        logs = list(backup_dir.glob("000_rsync_log_*.log"))
        assert len(logs) == 1
        assert "Rsync summary for" in logs[0].read_text()

    def test_rsync_integration_dry_run(self, tmp_path):
        src = tmp_path / "source"
        dst = tmp_path / "destination"
        src.mkdir()
        dst.mkdir()

        (src / "demo.txt").write_text("Dry run test")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = dst / f"000_rsync_backup_{timestamp}"

        rs.run_rsync(str(src), str(dst), str(backup_dir), dry_run=True)

        assert not (dst / "demo.txt").exists()
        assert not backup_dir.exists()

    def test_rsync_integration_delete_and_backup(self, tmp_path):
        src = tmp_path / "source"
        dst = tmp_path / "destination"
        src.mkdir()
        dst.mkdir()

        (src / "keep.txt").write_text("Keep this file")
        (dst / "keep.txt").write_text("Old version")
        (dst / "delete_me.txt").write_text("This should be deleted")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = dst / f"000_rsync_backup_{timestamp}"

        rs.run_rsync(str(src), str(dst), str(backup_dir), dry_run=False)

        assert not (dst / "delete_me.txt").exists()
        assert (dst / "keep.txt").read_text() == "Keep this file"

        backups = list(backup_dir.rglob("delete_me.txt"))
        assert len(backups) == 1
        assert backups[0].read_text() == "This should be deleted"

        logs = list(backup_dir.glob("000_rsync_log_*.log"))
        assert len(logs) == 1

    def test_safe_rsync_main_copy(self, tmp_path, script_path):
        src = tmp_path / "cli_src"
        dst = tmp_path / "cli_dst"
        src.mkdir()
        dst.mkdir()
        (src / "hello.txt").write_text("From CLI test")

        result = subprocess.run(
            ["python3", str(script_path), str(src), str(dst)],
            capture_output=True,
            text=True,
            check=True,
        )

        assert "✅ Rsync complete." in result.stdout
        assert (dst / "hello.txt").read_text() == "From CLI test"

        timestamp_prefix = datetime.now().strftime("000_rsync_backup_%Y-%m-%d_")
        backups = list(dst.glob(f"{timestamp_prefix}*/000_rsync_log_*.log"))
        assert backups

    def test_safe_rsync_main_dry_run(self, tmp_path, script_path):
        src = tmp_path / "cli_src"
        dst = tmp_path / "cli_dst"
        src.mkdir()
        dst.mkdir()
        (src / "test.txt").write_text("Dry run check")

        result = subprocess.run(
            ["python3", str(script_path), "-n", str(src), str(dst)],
            capture_output=True,
            text=True,
            check=True,
        )

        assert "🔍 Dry run" in result.stdout
        assert not (dst / "test.txt").exists()
