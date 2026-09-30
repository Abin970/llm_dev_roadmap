"""Importing this package registers all 7 tools -- each module's
`@register(...)` decorator runs as a side effect of being imported here.
Nothing to implement in this file; just `import tools` wherever you need
the registry populated (experiments, main.py, the agent loop/graph).

`apply_fix` (new in Week 4) is the one tool here that changes something
(even if only pretend) -- everything else is read-only. It's registered
like any other tool; what makes it "risky" is only how graph.py's
apply_fix_node chooses to call it (behind a human-approval interrupt),
not anything special about its registration.
"""
from . import (  # noqa: F401
    apply_fix,
    calculator,
    file_reader,
    search_docs,
    search_vendor_docs,
    sqlite_tool,
)
