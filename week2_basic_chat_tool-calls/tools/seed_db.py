"""One-time setup script: creates tools/sample.db with a couple of tables
for sqlite_tool.py's exercise to query against.

Complete and runnable as-is -- this is plumbing, not the learning
exercise. Run once:

    python tools/seed_db.py   (from inside week2/)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sample.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS incidents;
        CREATE TABLE incidents (
            id INTEGER PRIMARY KEY,
            service TEXT NOT NULL,
            severity TEXT NOT NULL,
            resolved INTEGER NOT NULL
        );

        DROP TABLE IF EXISTS deploys;
        CREATE TABLE deploys (
            id INTEGER PRIMARY KEY,
            service TEXT NOT NULL,
            version TEXT NOT NULL,
            deployed_at TEXT NOT NULL
        );
        """
    )

    cur.executemany(
        "INSERT INTO incidents (service, severity, resolved) VALUES (?, ?, ?)",
        [
            ("checkout-service", "high", 1),
            ("checkout-service", "low", 1),
            ("auth-service", "medium", 0),
            ("payments-service", "critical", 1),
        ],
    )
    cur.executemany(
        "INSERT INTO deploys (service, version, deployed_at) VALUES (?, ?, ?)",
        [
            ("checkout-service", "2.4.1", "2026-09-01"),
            ("auth-service", "1.9.0", "2026-09-05"),
        ],
    )

    conn.commit()
    conn.close()
    print(f"seeded {DB_PATH}")


if __name__ == "__main__":
    main()
