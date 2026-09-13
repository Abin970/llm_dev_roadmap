"""Thin wrapper around the OpenAI SDK.

Carried over unchanged from week1/llm_client.py -- you already implemented
and validated this. Nothing new to fill in here; week2's new exercise is
everything built on top of it (conversation.py, events.py, tools/).

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

One naming note from the docs: current examples use role "developer" where
older material (and Anthropic's API) says "system". Same concept, renamed.
Use "developer" going forward; recognize "system" when you see it elsewhere.
"""
from __future__ import annotations

import os
from typing import Iterator, TypeVar

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

MAX_TOKENS = 2000  # arbitrary, but a reasonable default for most tasks

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


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Exact token count of `text` under `model`'s tokenizer."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text))
