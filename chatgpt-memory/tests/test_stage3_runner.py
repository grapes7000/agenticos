import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location("run_stage3", SRC / "run_stage3.py")
run_stage3 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(run_stage3)


class Stage3RunnerTests(unittest.TestCase):
    def test_runner_processes_batches_then_finalizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite3"
            output = Path(tmp) / "memory"
            # Each batch checks queued once before and once after processing.
            # The final 0 is the loop-exit check.
            queue_counts = iter([5, 2, 2, 0, 0])

            def fake_scalar(_db, sql):
                if "state='failed'" in sql:
                    return 0
                return next(queue_counts)

            with (
                mock.patch.object(run_stage3, "queue_conversations", return_value={"queued": 5}) as queue,
                mock.patch.object(run_stage3, "scalar", side_effect=fake_scalar),
                mock.patch.object(run_stage3, "extract_queued", return_value={"processed": 3, "failed": 0, "items": 4}) as extract,
                mock.patch.object(run_stage3, "write_knowledge", return_value={"promoted": 4}) as write,
                mock.patch.object(run_stage3, "link_relations", return_value={"error_solution": 1}) as link,
                mock.patch.object(run_stage3, "finalize", return_value={"snapshots": {"snapshots": 1}}) as finish,
            ):
                result = run_stage3.run_all(db, "test-model", "127.0.0.1:11434", 3, 1, output)

            queue.assert_called_once()
            self.assertEqual(extract.call_count, 2)
            self.assertGreaterEqual(write.call_count, 3)
            self.assertGreaterEqual(link.call_count, 3)
            finish.assert_called_once_with(db, output)
            self.assertEqual(result["batches"], 2)
            self.assertEqual(result["extracted"], 6)

    def test_runner_rejects_invalid_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                run_stage3.run_all(Path(tmp) / "x.db", "m", "h", 0, 1, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
