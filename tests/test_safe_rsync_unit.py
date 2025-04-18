import re

import pytest
import safe_rsync as rs


@pytest.mark.unit
class TestUnit:
    """Unit tests for isolated components in safe_rsync.py"""

    def test_parse_rsync_version(self):
        """Test that rsync version output is parsed into a string and tuple."""
        out = "rsync  version  3.2.7  protocol 31\nCopyright (C) 1996-2022"
        ver_str, ver_tuple = rs.parse_rsync_version(out)

        assert ver_str == "3.2.7"
        assert ver_tuple == (3, 2, 7)

    def test_build_rsync_command_basics(self, tmp_path):
        """Test that build_rsync_command returns correct flags and structure."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        backup = tmp_path / "backup"
        src.mkdir()
        dst.mkdir()
        backup.mkdir()

        cmd = rs.build_rsync_command(
            src=str(src),
            dst=str(dst),
            backup_dir=str(backup),
            exclude_pattern="000_rsync_backup_*",
            dry_run=True,
        )

        assert cmd[:2] == ["rsync", "--dry-run"]

        joined = " ".join(cmd)
        for flag in ("-ah", "--delete", "--backup", "--info=stats2,progress2"):
            pattern = rf"(?:^|\s){re.escape(flag)}(?:\s|$)"
            assert re.search(pattern, joined)

    def test_check_platform(self, monkeypatch):
        """Test that Windows platform raises an error, while Linux/macOS passes."""
        monkeypatch.setattr("platform.system", lambda: "Linux")
        rs.check_platform()  # Should not raise

        monkeypatch.setattr("platform.system", lambda: "Windows")
        with pytest.raises(SystemExit):
            rs.check_platform()

    def test_check_rsync_good_version(self, monkeypatch):
        """Test that a valid rsync version passes the check."""
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

        fake_output = "rsync  version  3.2.7  protocol 31\n"
        monkeypatch.setattr(
            "subprocess.check_output",
            lambda cmd, text: fake_output,
        )

        # Should print a green success message and not raise
        rs.check_rsync()

    def test_check_rsync_too_old(self, monkeypatch):
        """Test that an outdated rsync version raises a SystemExit."""
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

        old_output = "rsync  version  3.1.0  protocol 30\n"
        monkeypatch.setattr(
            "subprocess.check_output",
            lambda cmd, text: old_output,
        )

        with pytest.raises(SystemExit):
            rs.check_rsync()

    def test_check_rsync_missing(self, monkeypatch):
        """Test that missing rsync binary raises a SystemExit."""
        monkeypatch.setattr("shutil.which", lambda cmd: None)

        with pytest.raises(SystemExit):
            rs.check_rsync()

    def test_execute_rsync_success(self, monkeypatch):
        """Test that execute_rsync collects expected summary lines on success."""
        mock_lines = [
            "sending incremental file list\n",
            "to-chk=5/10\n",
            "Number of files: 10\n",
            "Total file size: 1234 bytes\n",
        ]

        class MockPopen:
            def __init__(self, *args, **kwargs):
                self.stdout = iter(mock_lines)
                self.returncode = 0

            def wait(self):
                return self.returncode

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: MockPopen())
        stats = rs.execute_rsync(["rsync", "dummy", "args"])
        assert "Total file size: 1234 bytes" in stats

    def test_execute_rsync_failure(self, monkeypatch):
        """Test that execute_rsync aborts on non-zero exit code."""

        class MockPopen:
            def __init__(self, *args, **kwargs):
                self.stdout = iter(["sending incremental file list\n"])
                self.returncode = 23

            def wait(self):
                return self.returncode

            def terminate(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: MockPopen())
        with pytest.raises(SystemExit):
            rs.execute_rsync(["rsync", "dummy", "args"])

    def test_run_rsync_dry_run(self, monkeypatch, tmp_path):
        """Test that run_rsync executes sub-components correctly in dry-run mode."""
        mock_cmd = ["rsync", "--dry-run"]
        monkeypatch.setattr(rs, "build_rsync_command", lambda *a, **k: mock_cmd)
        monkeypatch.setattr(rs, "print_rsync_header", lambda *a, **k: None)
        monkeypatch.setattr(rs, "execute_rsync", lambda *a, **k: ["Total file size: 1234"])
        monkeypatch.setattr(rs, "print_summary", lambda stats, duration: None)

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        backup = dst / "backup"

        rs.run_rsync(str(src), str(dst), str(backup), dry_run=True)

    def test_print_summary(self, capsys):
        """Test that print_summary outputs expected lines and formatting."""
        stats = [
            "Number of files: 3",
            "Total file size: 12345 bytes"
        ]
        duration = 2.34

        rs.print_summary(stats, duration)

        captured = capsys.readouterr()
        assert "✅ Rsync summary" in captured.out
        assert "Number of files: 3" in captured.out
        assert "Total file size: 12345 bytes" in captured.out
        assert "⏱ Duration: 2.34 seconds" in captured.out
