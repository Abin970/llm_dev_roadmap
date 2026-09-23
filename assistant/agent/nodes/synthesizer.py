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

from llm_client import chat


def synthesizer_node(state: GraphState) -> dict:

     system_prompt = (
        "You are the synthesis step of an SRE on-call copilot. Given an "
        "incident question and retrieved evidence, propose a root cause "
        "and a concrete fix.\n\n"
        "Rules:\n"
        "- Every claim you make MUST cite which evidence entry it comes "
        "from, e.g. '...idle connections recycled too fast [search_docs]...' "
        "or '...raising max_idle_time [search_web]...'.\n"
        "- Do not state anything as fact unless it's directly supported "
        "by the evidence below. If the evidence doesn't support a clear "
        "answer, say that explicitly instead of guessing.\n"
        "- Be concise: one short root cause, then one concrete fix."
    )

     user_content = f"Question: {state['question']}\n\nEvidence:\n{evidence_block}"

     messages = [
                 {"role": "developer", "content": system_prompt},
                 {"role": "user", "content": user_content},
             ]
     response = chat(messages,max_tokens=2000)

     return {"synthesis": chat(response)}