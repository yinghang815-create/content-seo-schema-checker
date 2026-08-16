from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str, expected: int) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, "-m", "content_seo_checker", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(expected, completed.returncode, completed.stderr)
        return completed

    def test_json_report_and_failure_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.html"
            source.write_text("<h2>Page</h2>", encoding="utf-8")
            completed = self.run_cli(str(source), "--report", "json", expected=1)

        report = json.loads(completed.stdout)
        self.assertGreater(report["summary"]["error"], 0)
        self.assertEqual(1, report["summary"]["documents"])

    def test_directory_scan_and_never_fail_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.md").write_text("# One", encoding="utf-8")
            (root / "skip.txt").write_text("not scanned", encoding="utf-8")
            completed = self.run_cli(str(root), "--fail-on", "never", expected=0)

        self.assertIn("Checked 1 document(s)", completed.stdout)

    def test_sarif_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "one.md"
            output = root / "report.sarif"
            source.write_text("# One", encoding="utf-8")
            self.run_cli(
                str(source),
                "--report",
                "sarif",
                "--output",
                str(output),
                "--fail-on",
                "never",
                expected=0,
            )
            sarif = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual("2.1.0", sarif["version"])


if __name__ == "__main__":
    unittest.main()
