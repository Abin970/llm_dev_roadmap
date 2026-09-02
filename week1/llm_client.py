"""Thin wrapper around the OpenAI SDK.

Deliberately thin: Week 1's goal is to see the raw request/response shape
yourself, before any framework hides it. Fill in every TODO below yourself --
this file *is* the exercise, not scaffolding around it.

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

MAX_TOKENS = 2000  # arbitrary, but a reasonable default for most tasks

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


"""
	Return a process-wide OpenAI client, creating it once.

    TODO:
      - if _client is None, construct OpenAI() -- no arguments needed,
        the SDK reads OPENAI_API_KEY from the environment for you
      - cache it in the module-level `_client` (you'll need `global _client`)
      - return it
"""
def get_client() -> OpenAI:
	global _client
	if _client is None:
		_client = OpenAI()

	return _client



"""
	One non-streaming call. Return just the text of the reply.

    TODO:
      1. call get_client().chat.completions.create(
             model=model, messages=messages, temperature=temperature,
             max_tokens=max_tokens,
         )
      2. return completion.choices[0].message.content
"""
def chat(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 1.0,
    max_tokens: int = MAX_TOKENS,
) -> str:
	completions = get_client().chat.completions.create(
    model=model, messages=messages, temperature=temperature,
    max_completion_tokens=max_tokens,
	)

	return completions.choices[0].message.content


"""
	Streaming call. Yield text deltas as they arrive.

	Deliberately using the raw stream=True path here, not the higher-level
	`.stream()` helper -- the point this week is to see actual SSE delta
	chunks with your own eyes, not to call a helper that hides them.

	TODO:
	  1. call get_client().chat.completions.create(
			 model=model, messages=messages, temperature=temperature,
			 stream=True,
		 )
		 this returns an iterator of ChatCompletionChunk, not a ChatCompletion
	  2. for chunk in that iterator:
			 delta = chunk.choices[0].delta.content
			 if delta is not None: yield delta
"""
def chat_stream(
	messages: list[dict],
    *,
	model: str = DEFAULT_MODEL,
	temperature: float = 1.0,
	max_tokens: int = MAX_TOKENS,
) -> Iterator[str]:
	
	chatCompletionIterator = get_client().chat.completions.create(
		model=model, messages=messages, temperature=temperature,
		max_tokens=max_tokens, stream=True,
	)
	for chunk in chatCompletionIterator:
		delta = chunk.choices[0].delta.content
		if delta is not None: yield delta


"""
	Call with a Pydantic model as the response schema (schema-constrained
    decoding, not "please output JSON" prompting). Return a parsed instance
    of `schema`, or None if the model refused.

    TODO:
      1. call get_client().chat.completions.parse(
             model=model, messages=messages, response_format=schema,
         )
      2. message = completion.choices[0].message
      3. if message.parsed is not None: return it
         else: print(message.refusal) and return None
"""
def chat_structured(
    messages: list[dict],
    schema: type[T],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
) -> T | None:

	completion = get_client().chat.completions.parse(
		model=model, messages=messages, response_format=schema,
		max_tokens=max_tokens,
	)
	message = completion.choices[0].message

	if message.parsed is not None:
		return message.parsed
	else :
		return None

"""
	Exact token count of `text` under `model`'s tokenizer.

    TODO:
      - tiktoken ships a fixed table of known model names and won't
        recognize a brand-new model id immediately. Try
        `tiktoken.encoding_for_model(model)`; on KeyError, fall back to
        `tiktoken.get_encoding("o200k_base")` (the current-generation
        encoding shared by recent models).
      - return len(encoding.encode(text))
	"""
def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:

	encoding = None
	try:
		encoding = tiktoken.encoding_for_model(model)
	except KeyError:
		encoding = tiktoken.get_encoding("o200k_base")
	return len(encoding.encode(text))