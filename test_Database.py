import tempfile
import unittest
from pathlib import Path

import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        fd, temp_path = tempfile.mkstemp(suffix=".db")
        import os

        os.close(fd)
        os.unlink(temp_path)
        self.db_path = Path(temp_path)

    def tearDown(self):
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except PermissionError:
                pass

    def test_initialize_database_creates_table(self):
        database.initialize_database(self.db_path)
        with database.get_connection(self.db_path) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='snapshots'"
            ).fetchall()
        self.assertEqual(len(tables), 1)

    def test_save_snapshot_and_count(self):
        database.initialize_database(self.db_path)
        metrics = {
            "timestamp": "2026-01-01T00:00:00Z",
            "hostname": "host-a",
            "cpu_percent": 42.0,
            "memory_percent": 55.0,
            "disk_percent": 70.0,
            "memory_available_mb": 1500.0,
            "swap_percent": 20.0,
            "disk_read_bytes_per_sec": 100.0,
            "disk_write_bytes_per_sec": 200.0,
            "network_recv_bytes_per_sec": 300.0,
            "network_sent_bytes_per_sec": 400.0,
            "load_average": [0.5, 0.4, 0.3],
            "cpu_count": 8,
            "top_memory_processes": [{"pid": 1, "name": "init", "memory_percent": 5.0}],
        }

        row_id = database.save_snapshot(metrics, self.db_path)
        self.assertGreater(row_id, 0)
        self.assertEqual(database.get_snapshot_count(self.db_path), 1)

    def test_get_recent_snapshots_round_trip(self):
        database.initialize_database(self.db_path)
        row = {
            "timestamp": "2026-01-01T00:00:01Z",
            "hostname": "host-b",
            "cpu_percent": 66.0,
            "memory_percent": 72.0,
            "disk_percent": 81.0,
            "memory_available_mb": 1200.0,
            "swap_percent": 26.0,
            "disk_read_bytes_per_sec": 10.0,
            "disk_write_bytes_per_sec": 20.0,
            "network_recv_bytes_per_sec": 30.0,
            "network_sent_bytes_per_sec": 40.0,
            "load_average": [1.0, 0.7, 0.6],
            "cpu_count": 4,
            "top_memory_processes": [],
        }
        database.save_snapshot(row, self.db_path)
        result = database.get_recent_snapshots(limit=5, database_path=self.db_path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["hostname"], "host-b")


if __name__ == "__main__":
    unittest.main()
