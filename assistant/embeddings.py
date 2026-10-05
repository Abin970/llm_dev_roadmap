"""embeddings.py -- text -> vectors, the "embed" step.

Verified against the installed openai==3.5.0 SDK and the live API with
this project's key (2026-09-30):

  get_client().embeddings.create(model="text-embedding-3-small", input=[...])
    -> response.data[i].embedding : list[float], length 1536
       response.data[i].index     : position in `input` (order by this)
       response.usage.total_tokens
  - Reuse llm_client.get_client(). It reads OPENAI_API_KEY_LLM_PRJ; a
    bare OpenAI() picks up whatever OPENAI_API_KEY your shell has (a
    different key, with different model access).
  - Vectors come back with norm ~0.9997, not exactly 1.0. Normalize the
    rows yourself so inner product == cosine exactly (FaissStore relies
    on it).
  - `dimensions=256` returns shorter, re-normalized vectors (optional).
  - Limits: <= 8,192 tokens per input, <= 300,000 tokens per request.
      ""             -> BadRequestError 400 "input cannot be an empty string"
      8,193+ tokens  -> BadRequestError 400 "maximum input length is 8192 tokens"
    So drop empty texts upstream (chunkers), and batch by TOKEN count,
    not by item count. Count tokens with tiktoken's "cl100k_base",
    which is what tiktoken.encoding_for_model() returns for this model.
  - 429/5xx/timeouts: the SDK already retries twice with backoff
    (OpenAI(max_retries=2) is the default -- verified). Anything past
    that surfaces as an exception; let it fail loudly, since a
    half-embedded index is worse than none.

TODO (yours): OpenAIEmbedder.embed / embed_query below. Also track the
total tokens embedded on the instance (sum usage.total_tokens), so
pipeline.py can print what an ingestion run cost. Week 7's cost
tracking wants the same number. The price per 1M tokens is on OpenAI's
pricing page; the whole corpus (~900k tokens) costs cents.

A local model (fastembed, ONNX, no PyTorch) is a second Embedder
implementation in Week 6. Its default model reads at most 512 tokens per
input, which is why it isn't this week's default: exercise 2 compares
chunk sizes and would be quietly skewed by that cutoff. Whichever model
built an index must also embed the queries against it. Vectors from two
models don't live in the same space (the artifact's own warning).
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from llm_client import get_client, count_tokens  # noqa: F401  (you'll need it)

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
MAX_TOKENS_PER_INPUT = 8192
MAX_TOKENS_PER_REQUEST = 300_000
MAX_INPUTS_PER_REQUEST = 2048

# curl https://api.openai.com/v1/embeddings \
#   -H "Authorization: Bearer $OPENAI_API_KEY" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "input": "Hello world",
#     "model": "text-embedding-3-small",
#     "encoding_format": "float",
#     "dimensions": 3
#   }'

# {
#   "object": "list",
#   "data": [
#     {
#       "object": "embedding",
#       "embedding": [
#         0.26726124,
#         0.53452248,
#         0.80178373
#       ],
#       "index": 0
#     }
#   ],
#   "model": "text-embedding-3-small",
#   "usage": {
#     "prompt_tokens": 2,
#     "total_tokens": 2
#   }
# }

class Embedder(Protocol):
    model: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
         """(len(texts), dim) float32, L2-normalized rows, same order as texts."""
         ...
    def embed_query(self, text: str) -> np.ndarray:
       """(dim,) float32, normalized -- the query side of retrieval."""
       ...


class OpenAIEmbedder:
    model = EMBED_MODEL
    dim = EMBED_DIM

    def __init__(self) -> None:
        self.tokens_used = 0
        
    

    def embed(self, texts: list[str]) -> np.ndarray:
       if not texts:
        return np.empty((0, EMBED_DIM), dtype=np.float32)
       
       total_request_token = 0
       batch = []
       request_batches = []
       embedding_array = []
       for i,text in enumerate(texts):
           if not text.strip():
            raise ValueError(f"text {i} is empty")
             
           token_count = count_tokens(text, model= EMBED_MODEL)
           if token_count> MAX_TOKENS_PER_INPUT:
              raise ValueError(
                 f"text {i}: {text} exceeds token limit {MAX_TOKENS_PER_INPUT}"
                )
          
           if(total_request_token+token_count> MAX_TOKENS_PER_REQUEST
              or len(batch) >= MAX_INPUTS_PER_REQUEST):
             request_batches.append(batch)
             batch=[]
             total_request_token=token_count
           else: 
             total_request_token += token_count
        
           batch.append(text)

       if batch:   
           request_batches.append(batch)
        
       for batch in request_batches:
          response = get_client().embeddings.create(
              model = EMBED_MODEL,
              input = batch
          )
          response.data.sort(key = lambda  data:data.index)
          vectors=np.array([item.embedding for item in response.data], dtype=np.float32)   # shape (batch_size, 1536)
          embedding_array.append(vectors)
          self.tokens_used += response.usage.total_tokens

       result = np.vstack(embedding_array)
       norms = np.linalg.norm(result, axis=1, keepdims=True)
       result = result / norms
       return result
          

    def embed_query(self, text: str) -> np.ndarray:
       return self.embed([text])[0]        
