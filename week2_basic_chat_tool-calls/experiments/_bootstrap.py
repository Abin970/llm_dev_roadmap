"""Shared import shim so `experiments/*.py` can `from llm_client import ...`
and `import tools` without turning week2 into an installed package. Each
experiment does:

    import _bootstrap  # noqa: F401

Nothing to implement here -- this is plumbing, not a learning exercise.
"""
import sys
from pathlib import Path

week2_dir = Path(__file__).resolve().parent.parent
if str(week2_dir) not in sys.path:
    sys.path.insert(0, str(week2_dir))
