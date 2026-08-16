import os
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grid_ops_arena import safeio
from grid_ops_arena.policies import get_policy
from grid_ops_arena.reporting import write_reports
from grid_ops_arena.simulator import build_demo_scenario, simulate


REPORT_NAMES = (
    "grid_ops_report.json",
    "grid_ops_report.md",
    "grid_ops_report.html",
)


class SafeOutputTests(unittest.TestCase):
    def setUp(self):
        self.result = simulate(build_demo_scenario(3, 12), get_policy("balanced"))

    def test_every_preexisting_report_symlink_is_rejected_without_partial_output(self):
        for name in REPORT_NAMES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "out"
                output.mkdir()
                sentinel = root / "sentinel.txt"
                sentinel.write_text("do not replace", encoding="utf-8")
                (output / name).symlink_to(sentinel)
                with self.assertRaisesRegex(ValueError, "non-regular"):
                    write_reports(self.result, output)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not replace")
                self.assertEqual(sorted(path.name for path in output.iterdir()), [name])

    def test_symlinked_output_directory_and_non_directory_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_output = root / "real"
            real_output.mkdir()
            linked_output = root / "linked"
            linked_output.symlink_to(real_output, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory"):
                write_reports(self.result, linked_output)
            self.assertEqual(list(real_output.iterdir()), [])

            blocked = root / "blocked"
            blocked.write_text("file, not directory", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "real directory"):
                write_reports(self.result, blocked / "nested")

    def test_cli_rejects_linked_output_but_reads_an_explicit_input_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT / "src")
            scenario_link = root / "scenario.json"
            scenario_link.symlink_to(ROOT / "examples" / "synthetic_scenario.json")
            output = root / "out"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grid_ops_arena",
                    "run",
                    "--scenario",
                    str(scenario_link),
                    "--output-dir",
                    str(output),
                ],
                cwd=str(ROOT),
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((output / "grid_ops_report.json").is_file())

            real_output = root / "real"
            real_output.mkdir()
            linked_output = root / "linked"
            linked_output.symlink_to(real_output, target_is_directory=True)
            rejected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grid_ops_arena",
                    "demo",
                    "--hours",
                    "12",
                    "--output-dir",
                    str(linked_output),
                ],
                cwd=str(ROOT),
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertNotIn("Traceback", rejected.stderr)
            self.assertEqual(list(real_output.iterdir()), [])

    @unittest.skipUnless(safeio._descriptor_io_available(), "requires descriptor-relative I/O")
    def test_directory_race_error_closes_every_open_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            opened = []
            closed = []
            original_open = os.open
            original_close = os.close

            def tracked_open(*args, **kwargs):
                descriptor = original_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            def tracked_close(descriptor):
                closed.append(descriptor)
                original_close(descriptor)

            with mock.patch.object(safeio.os, "open", side_effect=tracked_open), mock.patch.object(
                safeio.os, "close", side_effect=tracked_close
            ), mock.patch.object(safeio.os, "fstat", side_effect=OSError("synthetic race")):
                with self.assertRaisesRegex(OSError, "synthetic race"):
                    safeio._open_directory(Path(directory))
            self.assertCountEqual(opened, closed)

    def test_fallback_checks_a_linked_parent_before_creating_children(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with mock.patch.object(safeio, "_DESCRIPTOR_IO_AVAILABLE", False):
                with self.assertRaisesRegex(ValueError, "real directories"):
                    safeio.write_text_files(linked / "must-not-exist", {"x.txt": "x"})
            self.assertFalse((real / "must-not-exist").exists())

    def test_fallback_stream_setup_failure_closes_temp_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = []
            original_mkstemp = safeio.tempfile.mkstemp

            def tracked_mkstemp(*args, **kwargs):
                descriptor, path = original_mkstemp(*args, **kwargs)
                captured.append((descriptor, path))
                return descriptor, path

            with mock.patch.object(
                safeio, "_DESCRIPTOR_IO_AVAILABLE", False
            ), mock.patch.object(
                safeio.tempfile, "mkstemp", side_effect=tracked_mkstemp
            ), mock.patch.object(
                safeio.os, "fdopen", side_effect=OSError("synthetic stream failure")
            ):
                with self.assertRaisesRegex(OSError, "synthetic stream failure"):
                    safeio.write_text_files(Path(directory), {"x.txt": "x"})

            descriptor, temporary = captured[0]
            try:
                os.fstat(descriptor)
            except OSError:
                pass
            else:
                os.close(descriptor)
                self.fail("fallback temporary descriptor remained open")
            self.assertFalse(Path(temporary).exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_directory_locking_fails_closed_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "must-not-exist"
            with mock.patch.object(safeio, "fcntl", None):
                with self.assertRaisesRegex(OSError, "locking is unavailable"):
                    safeio.write_text_files(output, {"x.txt": "x"})
            self.assertFalse(output.exists())

    def test_two_concurrent_empty_directory_writers_never_mix_bundles(self):
        for iteration in range(10):
            with self.subTest(iteration=iteration), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "out"
                names = ["artifact-{0:02d}.txt".format(index) for index in range(20)]
                barrier = threading.Barrier(2)

                def publish(token):
                    barrier.wait()
                    safeio.write_text_files(
                        output, {name: token for name in names}
                    )

                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(publish, token) for token in ("A", "B")
                    ]
                    for future in futures:
                        future.result()

                values = {(output / name).read_text(encoding="utf-8") for name in names}
                self.assertIn(values, ({"A"}, {"B"}))
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()), sorted(names)
                )

    @unittest.skipUnless(safeio._descriptor_io_available(), "requires descriptor-relative I/O")
    def test_post_rename_error_is_reconciled_before_rollback(self):
        for preexisting in (False, True):
            with self.subTest(preexisting=preexisting), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                files = {"a.txt": "new-a", "b.txt": "new-b", "c.txt": "new-c"}
                if preexisting:
                    for name in files:
                        (output / name).write_text("old-" + name[0], encoding="utf-8")
                original_rename = os.rename
                injected = {"done": False}

                def move_then_fail(*args, **kwargs):
                    result = original_rename(*args, **kwargs)
                    if not injected["done"]:
                        injected["done"] = True
                        raise OSError("synthetic post-rename failure")
                    return result

                with mock.patch.object(safeio.os, "rename", side_effect=move_then_fail):
                    with self.assertRaisesRegex(OSError, "post-rename"):
                        safeio.write_text_files(output, files)

                expected = sorted(files) if preexisting else []
                self.assertEqual(sorted(path.name for path in output.iterdir()), expected)
                if preexisting:
                    for name in files:
                        self.assertEqual(
                            (output / name).read_text(encoding="utf-8"),
                            "old-" + name[0],
                        )

    def test_fallback_post_replace_error_is_reconciled_before_rollback(self):
        for preexisting in (False, True):
            with self.subTest(preexisting=preexisting), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                files = {"a.txt": "new-a", "b.txt": "new-b", "c.txt": "new-c"}
                if preexisting:
                    for name in files:
                        (output / name).write_text("old-" + name[0], encoding="utf-8")
                original_replace = os.replace
                injected = {"done": False}

                def move_then_fail(*args, **kwargs):
                    result = original_replace(*args, **kwargs)
                    if not injected["done"]:
                        injected["done"] = True
                        raise OSError("synthetic post-replace failure")
                    return result

                with mock.patch.object(
                    safeio, "_DESCRIPTOR_IO_AVAILABLE", False
                ), mock.patch.object(
                    safeio.os, "replace", side_effect=move_then_fail
                ):
                    with self.assertRaisesRegex(OSError, "post-replace"):
                        safeio.write_text_files(output, files)

                expected = sorted(files) if preexisting else []
                self.assertEqual(sorted(path.name for path in output.iterdir()), expected)
                if preexisting:
                    for name in files:
                        self.assertEqual(
                            (output / name).read_text(encoding="utf-8"),
                            "old-" + name[0],
                        )

    @unittest.skipUnless(safeio._descriptor_io_available(), "requires descriptor-relative I/O")
    def test_mid_commit_failure_restores_the_complete_previous_set(self):
        for preexisting in (False, True):
            with self.subTest(preexisting=preexisting), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                files = {"a.txt": "new-a", "b.txt": "new-b", "c.txt": "new-c"}
                if preexisting:
                    for name in files:
                        (output / name).write_text("old-" + name[0], encoding="utf-8")
                original_rename = os.rename
                calls = {"count": 0}
                failure_call = 5 if preexisting else 2

                def fail_during_commit(*args, **kwargs):
                    calls["count"] += 1
                    if calls["count"] == failure_call:
                        raise OSError("synthetic commit failure")
                    return original_rename(*args, **kwargs)

                with mock.patch.object(safeio.os, "rename", side_effect=fail_during_commit):
                    with self.assertRaisesRegex(OSError, "synthetic commit failure"):
                        safeio.write_text_files(output, files)

                expected = sorted(files) if preexisting else []
                self.assertEqual(sorted(path.name for path in output.iterdir()), expected)
                if preexisting:
                    for name in files:
                        self.assertEqual(
                            (output / name).read_text(encoding="utf-8"),
                            "old-" + name[0],
                        )


if __name__ == "__main__":
    unittest.main()
