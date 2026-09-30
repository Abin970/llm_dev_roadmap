"""sqlite_query -- run a read-only query against a small sample database.

Run tools/seed_db.py once to create sample.db (that script is complete,
nothing to implement there -- it's plumbing, not the exercise). This tool
is the exercise: reject anything that isn't a read, execute the query,
and turn the result into readable text.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import BaseModel

from .registry import register

DB_PATH = Path(__file__).resolve().parent / "sample.db"


class SqliteQueryArgs(BaseModel):
    query: str


@register("sqlite_query", SqliteQueryArgs)
def sqlite_query(args: SqliteQueryArgs) -> str:
    """
    TODO:
      1. Reject the query unless it starts with SELECT (case-insensitive,
         .strip() first) -- raise ValueError otherwise. A "query" tool
         that can also run INSERT/UPDATE/DROP is a write tool wearing a
         read tool's name; the model should never get that by accident.
      2. Open a connection to DB_PATH, execute args.query, fetchall().
      3. Format the rows into a readable string (one row per line is
         fine) and return it. If there are zero rows, return something
         like "(no results)" rather than an empty string.
    """
    if not args.query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(args.query)
        rows = cursor.fetchall()
        if not rows:
            return "(no results)"
        return "\n".join(str(row) for row in rows)
