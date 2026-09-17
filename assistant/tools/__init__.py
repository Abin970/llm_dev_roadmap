"""Importing this package registers all 6 tools -- each module's
`@register(...)` decorator runs as a side effect of being imported here.
Nothing to implement in this file; just `import tools` wherever you need
the registry populated (experiments, main.py, the agent loop)."""
from . import (  # noqa: F401
    calculator,
    file_reader,
    search_docs,
    search_web,
    sqlite_tool,
)
