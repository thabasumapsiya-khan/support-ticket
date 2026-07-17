import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import app


class TicketPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_dir = Path(__file__).resolve().parent.parent
        self.output_dir = self.base_dir / "output"
        self.json_path = self.output_dir / "results.json"
        self.csv_path = self.output_dir / "results.csv"
        self.output_dir.mkdir(exist_ok=True)
        if self.json_path.exists():
            self.json_path.unlink()
        if self.csv_path.exists():
            self.csv_path.unlink()

    def tearDown(self) -> None:
        if self.json_path.exists():
            self.json_path.unlink()
        if self.csv_path.exists():
            self.csv_path.unlink()

    def test_single_ticket_persistence_and_history(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/classify",
            json={"subject": "Cannot login", "body": "I reset my password several times."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.json_path.exists())
        self.assertTrue(self.csv_path.exists())

        history = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["subject"], "Cannot login")
        self.assertEqual(history[0]["body"], "I reset my password several times.")

        saved_response = client.get("/tickets")
        self.assertEqual(saved_response.status_code, 200)
        saved_payload = saved_response.json()
        self.assertEqual(len(saved_payload), 1)
        self.assertEqual(saved_payload[0]["subject"], "Cannot login")


if __name__ == "__main__":
    unittest.main()
