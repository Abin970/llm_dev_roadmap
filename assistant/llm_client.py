"""Thin wrapper around the OpenAI SDK.

Carried over from week2/llm_client.py, plus one new function this week:
`chat_with_tools`. Everything else here is already implemented and
validated -- your only new TODO in this file is that one function.

Confirmed current API shape (openai==3.5.0, via official SDK docs, Aug 2026):

  - client.chat.completions.create(model=..., messages=[...]) -> ChatCompletion
        completion.choices[0].message.content is the reply text

  - streaming: client.chat.completions.create(..., stream=True)
        -> Stream[ChatCompletionChunk], an iterator
        each chunk.choices[0].delta.content is the new text fragment,
        or None on chunks that carry no content (e.g. the first one,
        which only announces the role)

  - structured output: client.chat.completions.parse(model=..., messages=[...],
        response_format=SomePydanticModel) -> ParsedChatCompletion
        completion.choices[0].message.parsed is a `SomePydanticModel` instance,
        or None with .refusal set if the model declined

  - tool calling (NEW this week, confirmed directly against the installed
    openai==3.5.0 SDK's type definitions, Sep 2026):
    client.chat.completions.create(model=..., messages=[...], tools=[...])
        -> ChatCompletion, same as a normal call
        completion.choices[0].message.tool_calls is a list of tool calls
        (or None) -- each has .id (str), .type ("function"), and
        .function.name (str) / .function.arguments (a JSON STRING, not a
        dict -- you must json.loads it yourself)
        completion.choices[0].message.content is None when the model
        chose to call a tool instead of replying with text

One naming note from the docs: current examples use role "developer" where
older material (and Anthropic's API) says "system". Same concept, renamed.
Use "developer" going forward; recognize "system" when you see it elsewhere.
"""
from __future__ import annotations

import os
from typing import Any, Iterator, TypeVar

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

# Fallback only for if OPENAI_MODEL isn't set in .env -- the real per-week
# tiering (cheap for Week 1-2, mid for Week 3-5, frontier for Week 6-8) lives
# in .env; see .env.example for the table.
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-nano")
api_key = os.environ.get("OPENAI_API_KEY_LLM_PRJ")

MAX_TOKENS = 5000  # arbitrary, but a reasonable default for most tasks

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Return a process-wide OpenAI client, creating it once."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def chat(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 1.0,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """One non-streaming call. Return just the text of the reply."""
    completions = get_client().chat.completions.create(
        model=model, messages=messages, temperature=temperature,
        max_completion_tokens=max_tokens,
    )
    return completions.choices[0].message.content


def chat_stream(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 1.0,
    max_tokens: int = MAX_TOKENS,
) -> Iterator[str]:
    """Streaming call. Yield text deltas as they arrive."""
    chatCompletionIterator = get_client().chat.completions.create(
        model=model, messages=messages, temperature=temperature,
        max_tokens=max_tokens, stream=True,
    )
    for chunk in chatCompletionIterator:
        delta = chunk.choices[0].delta.content
        if delta is not None:
            yield delta


def chat_structured(
    messages: list[dict],
    schema: type[T],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
) -> T | None:
    """Call with a Pydantic model as the response schema (schema-constrained
    decoding). Return a parsed instance of `schema`, or None if the model
    refused."""
    completion = get_client().chat.completions.parse(
        model=model, messages=messages, response_format=schema,
        max_tokens=max_tokens,
    )
    message = completion.choices[0].message
    if message.parsed is not None:
        return message.parsed
    else:
        return None



"""New this week: same idea as `chat()`, but passes `tools` so the
    model can propose a tool call instead of just replying with text.

    Unlike `chat()`, this returns the raw SDK message object (not just
    `.content`) -- callers need to inspect both `.content` and
    `.tool_calls` to see which one the model actually did.
"""
def chat_with_tools(
    messages: list[dict],
    tools: list[dict[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
):
    
    """
    TODO: completed
      1. call get_client().chat.completions.create(
             model=model, messages=messages, tools=tools,
             max_completion_tokens=max_tokens,
         )
      2. return completion.choices[0].message

    """
    completion  = get_client().chat.completions.create(
        model=model, messages=messages, tools=tools,
        max_completion_tokens=max_tokens
    )
    return completion.choices[0].message

"""The returned message has:
    - .content: str | None -- text reply (None if it called a tool
        instead)
    - .tool_calls: list[...] | None -- each entry has .id,
        .function.name, .function.arguments (a JSON STRING -- json.loads
        it before using it as a dict of args)
"""



def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Exact token count of `text` under `model`'s tokenizer."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text))
