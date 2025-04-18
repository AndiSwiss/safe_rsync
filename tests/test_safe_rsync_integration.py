from datetime import datetime

import pytest
import safe_rsync as rs


@pytest.mark.integration
class TestIntegration:
    def test_rsync_integration_copy(self, tmp_path):
        src = tmp_path / "source"
        dst = tmp_path / "destination"
        src.mkdir()
        dst.mkdir()

        # Populate source
        (src / "file1.txt").write_text("Hello world")
        (src / "file2.log").write_text("Log content")
        (src / "subdir").mkdir()
        (src / "subdir" / "nested.txt").write_text("Nested content")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = dst / f"000_rsync_backup_{timestamp}"

        rs.run_rsync(str(src), str(dst), str(backup_dir), dry_run=False)

        # Files copied correctly
        assert (dst / "file1.txt").read_text() == "Hello world"
        assert (dst / "file2.log").read_text() == "Log content"
        assert (dst / "subdir" / "nested.txt").read_text() == "Nested content"

        # Log created
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

        # Should not copy
        assert not (dst / "demo.txt").exists()

        # Should not create backup/log
        assert not backup_dir.exists()

    def test_rsync_integration_delete_and_backup(self, tmp_path):
        src = tmp_path / "source"
        dst = tmp_path / "destination"
        src.mkdir()
        dst.mkdir()

        # Source with one updated file
        (src / "keep.txt").write_text("Keep this file")

        # Destination contains an outdated and an extra file
        (dst / "keep.txt").write_text("Old version")
        (dst / "delete_me.txt").write_text("This should be deleted")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = dst / f"000_rsync_backup_{timestamp}"

        rs.run_rsync(str(src), str(dst), str(backup_dir), dry_run=False)

        # Deleted file gone from destination
        assert not (dst / "delete_me.txt").exists()

        # Updated file content correct
        assert (dst / "keep.txt").read_text() == "Keep this file"

        # Deleted file exists in backup
        backups = list(backup_dir.rglob("delete_me.txt"))
        assert len(backups) == 1
        assert backups[0].read_text() == "This should be deleted"

        # Log exists
        logs = list(backup_dir.glob("000_rsync_log_*.log"))
        assert len(logs) == 1
