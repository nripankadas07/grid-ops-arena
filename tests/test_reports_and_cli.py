import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grid_ops_arena.policies import get_policy
from grid_ops_arena.reporting import write_reports
from grid_ops_arena.simulator import build_demo_scenario, simulate


class ReportingTests(unittest.TestCase):
    def test_all_report_formats(self):
        result = simulate(build_demo_scenario(2, 24), get_policy("resilience"))
        with tempfile.TemporaryDirectory() as directory:
            paths = write_reports(result, Path(directory))
            self.assertEqual(set(paths), {"json", "markdown", "html"})
            self.assertTrue(all(path.exists() for path in paths.values()))
            loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], "1.0.0")
            self.assertIn("Synthetic demo", paths["html"].read_text(encoding="utf-8"))

    def test_module_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                [sys.executable, "-m", "grid_ops_arena", "demo", "--seed", "5", "--hours", "24", "--output-dir", directory],
                cwd=str(ROOT),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((Path(directory) / "grid_ops_report.html").exists())

    def test_golden_demo_matches(self):
        result = simulate(build_demo_scenario(), get_policy("balanced"))
        with tempfile.TemporaryDirectory() as directory:
            paths = write_reports(result, Path(directory))
            golden = ROOT / "artifacts" / "demo"
            for path in paths.values():
                self.assertEqual(path.read_bytes(), (golden / path.name).read_bytes())

    def test_markdown_neutralizes_untrusted_scenario_text(self):
        scenario = build_demo_scenario(2, 24)
        scenario.scenario_id = (
            "safe`\n\n## FORGED SCORE ![pixel](https://attacker.invalid/p) "
            "[link](https://attacker.invalid) <https://attacker.invalid>"
        )
        result = simulate(scenario, get_policy("balanced"))
        with tempfile.TemporaryDirectory() as directory:
            markdown = write_reports(result, Path(directory))["markdown"].read_text(
                encoding="utf-8"
            )
        self.assertNotIn("\n## FORGED SCORE", markdown)
        self.assertIn("&#96;", markdown)
        self.assertNotIn("![pixel]", markdown)
        self.assertNotIn("](https://", markdown)
        self.assertNotIn("<https://", markdown)

    def test_cli_reports_invalid_config_without_traceback(self):
        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["config"]["battery_capacity_kwh"] = "120"
        with tempfile.TemporaryDirectory() as directory:
            scenario_path = Path(directory) / "invalid.json"
            scenario_path.write_text(json.dumps(artifact), encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grid_ops_arena",
                    "run",
                    "--scenario",
                    str(scenario_path),
                    "--output-dir",
                    str(Path(directory) / "out"),
                ],
                cwd=str(ROOT),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("grid-ops-arena: error:", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_cli_reports_derived_overflow_without_traceback(self):
        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["series"]["load_kw"][0] = 1e308
        artifact["config"]["timestep_hours"] = 1e308
        with tempfile.TemporaryDirectory() as directory:
            scenario_path = Path(directory) / "overflow.json"
            scenario_path.write_text(json.dumps(artifact), encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grid_ops_arena",
                    "run",
                    "--scenario",
                    str(scenario_path),
                    "--output-dir",
                    str(Path(directory) / "out"),
                ],
                cwd=str(ROOT),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("non-finite derived value", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
