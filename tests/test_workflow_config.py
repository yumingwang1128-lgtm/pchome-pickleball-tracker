from pathlib import Path
import unittest


class WorkflowConfigurationTests(unittest.TestCase):
    def test_collection_workflow_runs_daily_and_persists_database(self) -> None:
        workflow = Path(".github/workflows/collect.yml").read_text(encoding="utf-8")

        self.assertIn("schedule:", workflow)
        self.assertIn('cron: "0 1 * * *"', workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertIn("PYTHONPATH: src", workflow)
        self.assertIn("github.event.inputs.max_products", workflow)
        self.assertIn("git add data/tracker.db", workflow)


if __name__ == "__main__":
    unittest.main()
