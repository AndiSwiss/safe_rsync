import pytest
import safe_rsync as rs


# ────────────────────────────────────────────────────────────────────────
# 3. Platform check
# ────────────────────────────────────────────────────────────────────────
def test_check_platform(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    # Should not raise
    rs.check_platform()

    monkeypatch.setattr("platform.system", lambda: "Windows")
    with pytest.raises(SystemExit):
        rs.check_platform()


# ────────────────────────────────────────────────────────────────────────
# 4. rsync version detection
# ────────────────────────────────────────────────────────────────────────
def test_check_rsync_good_version(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

    fake_output = "rsync  version  3.2.7  protocol 31\n"
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, text: fake_output,
    )

    # Should print a green success message and not raise
    rs.check_rsync()


def test_check_rsync_too_old(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/rsync")

    old_output = "rsync  version  3.1.0  protocol 30\n"
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, text: old_output,
    )

    with pytest.raises(SystemExit):
        rs.check_rsync()


def test_check_rsync_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    with pytest.raises(SystemExit):
        rs.check_rsync()


# ────────────────────────────────────────────────────────────────────────
# 5. execute_rsync
# ────────────────────────────────────────────────────────────────────────
def test_execute_rsync_success(monkeypatch):
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


def test_execute_rsync_failure(monkeypatch):
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
def test_run_rsync_dry_run(monkeypatch, tmp_path):
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


def test_run_rsync_real(monkeypatch, tmp_path):
    stats_collected = []

    monkeypatch.setattr(rs, "build_rsync_command", lambda *a, **k: ["rsync", "--real"])
    monkeypatch.setattr(rs, "print_rsync_header", lambda *a, **k: None)
    monkeypatch.setattr(rs, "execute_rsync", lambda *a, **k: ["Total file size: 4321"])
    monkeypatch.setattr(rs, "print_summary", lambda stats, duration: stats_collected.extend(stats))
    monkeypatch.setattr(rs, "save_summary", lambda *a, **k: None)

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    backup = dst / "backup"

    rs.run_rsync(str(src), str(dst), str(backup), dry_run=False)
    assert "Total file size: 4321" in stats_collected
