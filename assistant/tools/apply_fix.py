"""apply_fix -- mocked remediation action for the SRE copilot.

TODO: same pattern as every other tool in this package -- a Pydantic
args schema plus a @register(...)-decorated handler. This one is
deliberately a no-op/mock (no real service or config is touched -- that's
a real product concern for much later, not this week's exercise): just
format and return a confirmation string describing what "would" happen,
e.g. given service="checkout-service", config_key="max_idle_time",
config_value="120s" ->
"applied: checkout-service.max_idle_time = 120s (mocked, no real change made)".

This is the one tool in the registry that graph.py's apply_fix_node gates
behind a human-approval interrupt() before ever calling dispatch() on it
-- everything else in this project's toolset (calculator, file_reader,
sqlite_query, search_docs, search_web) is read-only and safe to call
without asking anyone first; this is the first one that (pretends to)
change something.
"""
from __future__ import annotations

from pydantic import BaseModel

from .registry import register


class ApplyFixArgs(BaseModel):
    service: str
    config_key: str
    config_value: str


@register("apply_fix", ApplyFixArgs)
def apply_fix(args: ApplyFixArgs) -> str:
    """Apply a configuration fix to a service. MOCKED -- no real service
    or config is touched; this only returns a confirmation string. This
    is the one tool in the registry a caller should gate behind human
    approval before invoking, since it's the only one that changes
    anything (even if only pretend)."""

    return f"applied fix: {args.service}.{args.config_key}={args.config_value}"

    
