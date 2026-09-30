"""Shared import shim so `experiments/*.py` can `from llm_client import ...`
without turning week1 into an installed package. Each experiment does:

    from _bootstrap import week1_dir
    from llm_client import chat

Nothing to implement here -- this is plumbing, not a learning exercise.
"""
import sys
from pathlib import Path

week1_dir = Path(__file__).resolve().parent.parent
if str(week1_dir) not in sys.path:
    sys.path.insert(0, str(week1_dir))
