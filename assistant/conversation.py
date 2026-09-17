"""Conversation state + truncation strategies.

Why this exists: LLMs are stateless between calls -- the full message
history has to be re-sent every single turn. Left alone, that history
grows without bound and blows past the context window (and your token
budget) eventually. This file is where you decide what to do about that.

Two strategies to implement:
  - sliding window: just drop the oldest messages until you're back under
    budget. Cheap, but can silently drop a fact you still needed.
  - summarization: compress the oldest messages into one short summary
    message instead of deleting them outright. Costs an extra LLM call,
    keeps more signal.

One shared landmine for both: never truncate in a way that leaves a tool
result message with no matching tool-call message before it (or vice
versa) -- most providers reject a message list shaped like that. If you
drop one half of a tool-call/tool-result pair, drop both.

Run this file's own exercise: experiments/02_truncation_comparison.py
"""
from __future__ import annotations

from dataclasses import dataclass, field

from llm_client import DEFAULT_MODEL, chat, count_tokens


@dataclass
class ConversationState:
    messages: list[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
      """TODO: append {"role": role, "content": content} to self.messages."""
      self.messages.append({"role": role, "content": content})

    def token_count(self, model: str = DEFAULT_MODEL) -> int:
      """TODO: sum count_tokens(m["content"], model) across every message
      in self.messages and return the total."""
      return sum(count_tokens(m["content"], model) for m in self.messages)



def truncate_sliding_window(
    messages: list[dict], max_tokens: int, *, model: str = DEFAULT_MODEL
) -> list[dict]:
    """
    TODO: completed
      - Keep a leading system/developer message (index 0), if present,
        untouched -- it's instructions, not conversation history.
      - Drop the oldest remaining messages first, one at a time, until the
        total token count (see count_tokens) is <= max_tokens.
      - If dropping a message would separate a tool-call/tool-result pair,
        drop both messages of that pair together, not just one.
    """
    leading_message = messages[0] if messages and messages[0]["role"] in ("system", "developer") else None
    remaining_messsages = messages[1:] if leading_message else list(messages)
    token_count = ConversationState(messages=messages).token_count(model=model)

    while token_count > max_tokens and remaining_messsages:
      # Drop the oldest message (index 0) and recalculate token count
      dropped_message = remaining_messsages.pop(0)

      # If the dropped message is a tool-call, also drop the corresponding tool-result
      if is_tool_call(dropped_message):
        # Find and drop the corresponding tool-result message
        for i, msg in enumerate(remaining_messsages):
          if is_tool_result(msg):
            remaining_messsages.pop(i)
            break
          
      token_count = ConversationState(
               messages=[leading_message] + remaining_messsages if leading_message else remaining_messsages
            ).token_count(model=model)

    # Reassemble the final list of messages
    final_messages = [leading_message] + remaining_messsages if leading_message else remaining_messsages
    return final_messages
     

def truncate_summarize(
    messages: list[dict], max_tokens: int, *, model: str = DEFAULT_MODEL
) -> list[dict]:
    """
    TODO: completed
      - Keep a leading system/developer message untouched, and keep the
        most recent few turns verbatim (summarization is for the stuff
        about to fall out of the window, not the live conversation).
      - Take the oldest chunk of messages that needs to go, and instead of
        deleting them, call chat() with a prompt like "summarize the key
        facts from this conversation excerpt in 2-3 sentences", passing
        those messages' content as the thing to summarize.
      - Splice the result back in as a single message (role "developer" or
        "user", your call) in place of the messages it replaced, then
        return the full reassembled list.
    """
#
#[system, msg1, msg2, ..., msg28, msg29, msg30]
#
# if total_token>3/4*max_token
# summarize msg1 to msgi: sum(tokens(msg1..msgi))~1/2*max_token
# else if total_token<1/2*max_token
# summarize msg1 to msgi: sum(tokens(msg1..msgi))~1/4*max_token
#
    leading_message = messages[0] if messages and messages[0]["role"] in ("system", "developer") else None

    messages_to_summarize = context_to_summarize(messages[1:], max_tokens, model)

    if not messages_to_summarize['messages']:
        return messages  # No summarization needed
    
    joined_messages = "\n\n".join([msg["content"] for msg in messages_to_summarize['messages']])

    summarization_prompt = f"""summarize the key facts from this 
    conversation excerpt in 2-3 sentences.\n\n{joined_messages}"""

    summary_message = {"role": "developer", "content": summarization_prompt}

    summary = chat([summary_message], temperature=0.0, model=model)

    summary_message_out = {"role": "developer", "content": summary}

    final_messages = [summary_message_out] + messages[messages_to_summarize['index'] + 1:]

    return [leading_message] + final_messages if leading_message else final_messages



def context_to_summarize(messages: list[dict], max_tokens: int, model: str) -> dict:
    total_token_count = ConversationState(messages=messages).token_count(model=model)

    if total_token_count > (3 / 4) * max_tokens:
        target_token_count = (1 / 2) * max_tokens
    elif total_token_count < (1 / 2) * max_tokens:
        target_token_count = (1 / 4) * max_tokens
    else:
        return {'messages': [], 'index': -1}

    token_count = 0
    messages_to_summarize = []
    index_included=-1
    for i,msg in enumerate(messages):
        msg_token_count = count_tokens(msg["content"], model=model)
        if token_count + msg_token_count <= target_token_count:
            messages_to_summarize.append(msg)
            token_count += msg_token_count
            index_included=i
        else:
            break

    return {'messages':messages_to_summarize,'index':index_included}


def is_tool_call(msg: dict) -> bool:
    return bool(msg.get("tool_calls"))

def is_tool_result(msg: dict) -> bool:
    return msg.get("role") == "tool"