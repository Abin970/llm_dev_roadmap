"""Shared import shim so `experiments/*.py` can import from the assistant/
project (llm_client, conversation, events, tools, agent) without turning
it into an installed package. Each experiment does:

    import _bootstrap  # noqa: F401

Nothing to implement here -- this is plumbing, not a learning exercise.
"""
import sys
from pathlib import Path

assistant_dir = (Path(__file__).resolve().parent.parent.parent / "assistant").resolve()
if str(assistant_dir) not in sys.path:
    sys.path.insert(0, str(assistant_dir))
