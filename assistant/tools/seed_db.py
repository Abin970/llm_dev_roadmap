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
            symptom TEXT NOT NULL,
            severity TEXT NOT NULL,
            resolved INTEGER NOT NULL,
            incident_ref TEXT
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

    # NOTE: no fix/resolution is stored here on purpose -- resolved just
    # means "eventually closed out," not "here's how." incident_ref points
    # to a postmortem doc (search_docs) that explains root cause only; the
    # actual fix has to be reasoned out from separate tool/library docs
    # (search_vendor_docs), not read off a row.
    cur.executemany(
        "INSERT INTO incidents (service, symptom, severity, resolved, incident_ref) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("aurora-billing-sync", "connection pool exhausted under load, stale idle connections", "high", 1, "INC-4821"),
            ("checkout-service", "checkout failures during flash-sale traffic spikes, connection pool exhausted", "high", 1, "INC-5102"),
            ("auth-service", "token validation returning intermittent 401s", "medium", 0, None),
            ("payments-service", "webhook retries exceeding third-party rate limit, cascading 429s", "critical", 1, "INC-4990"),
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
