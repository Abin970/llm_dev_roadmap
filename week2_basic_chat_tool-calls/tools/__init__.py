"""Importing this package registers all 4 tools -- each module's
`@register(...)` decorator runs as a side effect of being imported here.
Nothing to implement in this file; just `import tools` wherever you need
the registry populated (experiments, main.py)."""
from . import calculator, file_reader, mock_search, sqlite_tool  # noqa: F401
