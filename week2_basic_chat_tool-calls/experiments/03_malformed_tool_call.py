"""
Experiment 3 -- Malformed tool-call handling
==================================================
Hypothesis : the model will eventually emit a tool call with bad
             arguments (wrong type, a missing required field, or a tool
             name that doesn't exist at all) -- your dispatch layer has to
             catch that, not the model.
Setup      : call dispatch() directly with a handful of deliberately bad
             payloads and confirm every one of them raises a clean
             ToolError instead of an unhandled exception.
Teaches    : never trust model output as pre-validated input -- this is
             the same lesson as never trusting client input to a public
             API endpoint.

Prerequisite: run `python tools/seed_db.py` once first.

Run: python experiments/03_malformed_tool_call.py
"""
import _bootstrap  # noqa: F401
import tools  # noqa: F401
from tools.registry import ToolError, dispatch

# TODO: list (tool_name, bad_args_dict) pairs covering at least:
#   - a missing required field (e.g. calculator with {} instead of
#     {"expression": ...})
#   - a wrong type (e.g. sqlite_query with {"query": 12345})
#   - a tool name that was never registered (e.g. "delete_database")
BAD_CALLS: list[tuple[str, dict]] = [
    # missing required field
    ("calculator", {}),
    ("file_reader", {}),
    ("sqlite_query", {}),
    ("search", {}),

    # wrong type for the field Pydantic expects
    ("calculator", {"expression": 42}),          # int instead of str
    ("sqlite_query", {"query": ["SELECT", 1]}),  # list instead of str

    # unknown tool name -- never registered at all
    ("delete_database", {"confirm": True}),

    # valid schema, but the *handler* itself should reject it
    # (these pass Pydantic validation, so they exercise the handler's
    # own try/except path in dispatch(), not the schema-validation path)
    ("calculator", {"expression": "__import__('os').system('echo hi')"}),  # not real arithmetic
    ("sqlite_query", {"query": "DROP TABLE incidents"}),                    # not a SELECT
    ("file_reader", {"filename": "../../.env"}),                            # path escapes sandbox
]


def main() -> None:
    for name, args in BAD_CALLS:
        # TODO: call dispatch(name, args) inside try/except ToolError.
        # Print a PASS line if ToolError was raised cleanly (with its
        # message); if ANY other exception type escapes, that's the bug
        # this experiment exists to catch -- let it crash loudly so you
        # notice, don't swallow it here.
        try:
            dispatch(name, args)
        except ToolError as e:
            print(f"PASS: {name} raised ToolError: {e}")
        except Exception as e:
            print(f"FAIL: {name} raised unexpected exception: {e}")
        else:
            print(f"FAIL: {name} did not raise any exception")


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did every bad call get caught as a clean ToolError? If something raised
# a different exception type instead (KeyError, TypeError, sqlite3.Error,
# ...), where exactly in dispatch()/the tool handler did validation miss
# it?

#
#PASS: calculator raised ToolError: 1 validation error for CalculatorArgs
#expression
#  Field required [type=missing, input_value={}, input_type=dict]
#    For further information visit https://errors.pydantic.dev/2.13/v/missing
#PASS: file_reader raised ToolError: 1 validation error for FileReaderArgs
#filename
#  Field required [type=missing, input_value={}, input_type=dict]
#    For further information visit https://errors.pydantic.dev/2.13/v/missing
#PASS: sqlite_query raised ToolError: 1 validation error for SqliteQueryArgs
#query
#  Field required [type=missing, input_value={}, input_type=dict]
#    For further information visit https://errors.pydantic.dev/2.13/v/missing
#PASS: search raised ToolError: 1 validation error for SearchArgs
#query
#  Field required [type=missing, input_value={}, input_type=dict]
#    For further information visit https://errors.pydantic.dev/2.1#3/v/missing
#
#
#

