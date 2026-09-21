"""synthesizer_node -- proposes a root cause + a concrete fix from the
gathered evidence, citing it.

TODO: call the LLM (llm_client.chat is enough -- no tool-calling needed
here, all the evidence is already sitting in state["evidence"]) with a
prompt along the lines of: "Given this evidence: {evidence}. Question:
{question}. Propose a root cause and a concrete fix, citing which piece
of evidence each claim comes from." On a retry (state["retry_count"] > 1),
also include state["review_verdict"] so the model knows what to fix
instead of just repeating the rejected answer verbatim.

    from llm_client import chat

    def synthesizer_node(state: GraphState) -> dict:
        content = chat([
            {"role": "developer", "content": "..."},
            {"role": "user", "content": "..."},
        ])
        return {"synthesis": content}

`chat()`'s signature (confirmed in llm_client.py, already implemented):
`chat(messages: list[dict], *, model=..., temperature=1.0, max_tokens=...) -> str`
-- it returns plain text, not a message object (that's chat_with_tools,
which this node doesn't need).

Keep the citation instruction explicit in the prompt -- reviewer_node's
grounding check (and week4/experiments/eval_checks.py's
check_grounding()) both depend on being able to trace each claim back to
an actual evidence entry, not just plausible-sounding prose.
"""
from __future__ import annotations

from llm_client import chat

from ..state import GraphState


def synthesizer_node(state: GraphState) -> dict:
    raise NotImplementedError
