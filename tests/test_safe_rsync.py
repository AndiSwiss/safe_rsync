import re

import pytest
import safe_rsync as rs


@pytest.mark.unit
class TestUnit:
    """Base class for unit tests."""

    # ────────────────────────────────────────────────────────────────────────
    # 1.  Parsing the rsync version string
    # ────────────────────────────────────────────────────────────────────────
    def test_parse_rsync_version(self):
        out = "rsync  version  3.2.7  protocol 31\nCopyright (C) 1996-2022"
        ver_str, ver_tuple = rs.parse_rsync_version(out)

        assert ver_str == "3.2.7"
        assert ver_tuple == (3, 2, 7)

    # ────────────────────────────────────────────────────────────────────────
    # 2.  Building the rsync command
    # ────────────────────────────────────────────────────────────────────────
    def test_build_rsync_command_basics(self, tmp_path):
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

        # The command must start with 'rsync --dry-run' …
        assert cmd[:2] == ["rsync", "--dry-run"]

        # …and contain the expected archive/delete switches.
        joined = " ".join(cmd)
        for flag in ("-ah", "--delete", "--backup", "--info=stats2,progress2"):
            pattern = rf"(?:^|\s){re.escape(flag)}(?:\s|$)"
            assert re.search(pattern, joined)

    # ────────────────────────────────────────────────────────────────────────
    # 3. Platform check
    # ────────────────────────────────────────────────────────────────────────
    def test_check_platform(self, monkeypatch):
        monkeypatch.setattr("platform.system", lambda: "Linux")
        # Should not raise
        rs.check_platform()

        monkeypatch.setattr("platform.system", lambda: "Windows")
        with pytest.raises(SystemExit):
            rs.check_platform()

    # ────────────────────────────────────────────────────────────────────────
    # 4. rsync version detection
    # ────────────────────────────────────────────────────────────────────────
    def test_check_rsync_good_version(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

        fake_output = "rsync  version  3.2.7  protocol 31\n"
        monkeypatch.setattr(
            "subprocess.check_output",
            lambda cmd, text: fake_output,
        )

        # Should print a green success message and not raise
        rs.check_rsync()

    def test_check_rsync_too_old(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

        old_output = "rsync  version  3.1.0  protocol 30\n"
        monkeypatch.setattr(
            "subprocess.check_output",
            lambda cmd, text: old_output,
        )

        with pytest.raises(SystemExit):
            rs.check_rsync()

    def test_check_rsync_missing(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        with pytest.raises(SystemExit):
            rs.check_rsync()

    # ────────────────────────────────────────────────────────────────────────
    # 5. execute_rsync
    # ────────────────────────────────────────────────────────────────────────
    def test_execute_rsync_success(self, monkeypatch):
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

    # ────────────────────────────────────────────────────────────────────────
    # 6. run_rsync orchestration logic
    # ────────────────────────────────────────────────────────────────────────
    def test_run_rsync_dry_run(self, monkeypatch, tmp_path):
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
