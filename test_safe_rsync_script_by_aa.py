import unittest
import os
import tempfile
from safe_rsync_script_by_aa import (
    get_abs,
    build_rsync_command,
    save_summary_log
)

class TestSafeRsyncHelpers(unittest.TestCase):

    def test_get_abs_expands_user_and_absolute_path(self):
        home_path = os.path.expanduser("~")
        self.assertEqual(get_abs("~"), home_path)
        self.assertTrue(os.path.isabs(get_abs("~/test")))

    def test_build_rsync_command_contains_all_expected_flags(self):
        src = "/source"
        dst = "/destination"
        backup_dir = "/destination/000_rsync_backup_2025-04-18_15-00-00"
        exclude_pattern = "000_rsync_backup_*"
        dry_run = True

        cmd = build_rsync_command(src, dst, backup_dir, exclude_pattern, dry_run)
        joined = " ".join(cmd)

        self.assertIn("rsync", cmd[0])
        self.assertIn("--delete", cmd)
        self.assertIn(f"--backup-dir={backup_dir}", cmd)
        self.assertIn(f"--exclude={exclude_pattern}", cmd)
        self.assertIn("--dry-run", cmd)
        self.assertIn("--info=stats2,progress2", joined)
        self.assertEqual(cmd[-2], src + "/")
        self.assertEqual(cmd[-1], dst)

    def test_save_summary_log_creates_and_writes_file(self):
        stats_lines = [
            "Number of files: 5",
            "Total file size: 12345 bytes",
        ]
        duration = 1.23

        with tempfile.TemporaryDirectory() as tempdir:
            log_path = os.path.join(tempdir, "test_rsync_log.txt")
            save_summary_log(stats_lines, log_path, duration)

            self.assertTrue(os.path.exists(log_path))

            with open(log_path) as f:
                content = f.read()
                self.assertIn("Number of files: 5", content)
                self.assertIn("Duration: 1.23 seconds", content)

if __name__ == '__main__':
    unittest.main()
