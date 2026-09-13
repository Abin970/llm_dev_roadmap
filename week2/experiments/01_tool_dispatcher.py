"""
Experiment 1 -- Tool dispatcher with 4 real tools
=======================================================
Objective  : wire calculator, file_reader, sqlite_query, and search behind
             one registry, and prove all four run through the exact same
             dispatch() call -- no tool gets special-cased.
Setup      : call dispatch(name, args) once per tool with a valid payload,
             print each result.
Teaches    : tools are a plugin interface, not per-tool logic scattered
             through your code.

Prerequisite: run `python tools/seed_db.py` once first (creates sample.db
for the sqlite_query tool).

Run: python experiments/01_tool_dispatcher.py
"""
import _bootstrap  # noqa: F401
import tools  # noqa: F401 -- importing this registers all 4 tools
from tools.registry import dispatch

# TODO: one call to dispatch() per tool, each with valid args for that
# tool's schema. Print the tool name and its result. Cover:
#   - "calculator"   e.g. {"expression": "2 + 2 * 3"}
#   - "file_reader"  e.g. {"filename": "notes.txt"}
#   - "sqlite_query" e.g. {"query": "SELECT * FROM incidents"}
#   - "search"       e.g. {"query": "checkout latency"}


def main() -> None:
    # Calculator tool
    calculator_args = {"expression": "2 + 2 * 3"}
    calculator_result = dispatch("calculator", calculator_args)
    print(f"Calculator result: {calculator_result}")

    # File Reader tool
    file_reader_args = {"filename": "notes.txt"}
    file_reader_result = dispatch("file_reader", file_reader_args)
    print(f"File Reader result: {file_reader_result}")

    # SQLite Query tool
    sqlite_query_args = {"query": "SELECT * FROM incidents"}
    sqlite_query_result = dispatch("sqlite_query", sqlite_query_args)
    print(f"SQLite Query result: {sqlite_query_result}")

    # Search tool
    search_args = {"query": "checkout latency"}
    search_result = dispatch("search", search_args)
    print(f"Search result: {search_result}")


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did all four tools go through dispatch() with zero tool-specific code in
# this file? If you had to add a special case for one of them, what did
# that reveal about a gap in the registry/dispatch design?
#
#
# yes all four tools went through dispatch() with zero tool-specific code in this file. 
# The design of the registry/dispatch system will be challenged when trying to add more complex tools.
# The current design's contract is "same input shape in (validated args),
# same output shape out (a string), executed synchronously and immediately, 
# with no extra info besides what the model sent." 
#

