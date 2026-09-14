# Providers

Everything external sits behind the four Protocols in `src/cloudops_rag/providers/base.py`
(`EmbeddingProvider`, `LLMProvider`, `RerankerProvider`, `SearchProvider`). Application code —
retrieval, generation, the API, the evaluation runner — never imports an SDK.

| Capability | `stub` | `bedrock` | `nvidia` |
|---|---|---|---|
| Embeddings | bag-of-words, deterministic | Titan Text Embeddings V2 | — |
| LLM | extractive, cites sources | Converse API (Nova Lite default) | NIM chat completions |
| Reranker | lexical overlap | Cohere Rerank 3.5 | — |
| Search | in-memory | — (OpenSearch is the single store) | — |

`stub` is what tests and the offline console run on. `bedrock` is the production runtime and
the only provider the AWS deployment accepts.

## NVIDIA NIM (optional, local dev + evaluation)

Approved deviation from the "one LLM provider implementation" rule (CLAUDE.md, 2026-09-15):
while Bedrock quotas are pending, generation and LLM-judged faithfulness can run against
NVIDIA's hosted endpoints (`https://integrate.api.nvidia.com/v1`, OpenAI-compatible).
It is an LLM provider only — embeddings and reranking stay stub/Bedrock, so retrieval-quality
numbers (Recall@K, MRR, NDCG) still require Titan. What it does unlock:

- `POST /ask` and the console with a real model instead of the extractive stub;
- `apps/evaluation/run.py --generation --judge`: answer faithfulness, citation validity,
  abstention behaviour, injection resistance — recorded with `llm: nvidia:<model>` in the report
  so they are never mistaken for Bedrock numbers.

Configuration (all from the environment; the key is a `SecretStr` and is never logged,
never in `/system`, never in a report):

```sh
LLM_PROVIDER=nvidia
LLM_MODEL=meta/llama-3.3-70b-instruct      # or nvidia/llama-3.1-nemotron-70b-instruct, meta/llama-3.1-8b-instruct
NVIDIA_API_KEY=nvapi-...                   # from build.nvidia.com; .env is gitignored
ALLOW_NVIDIA_CALLS=true                    # same explicit gate as ALLOW_AWS_CALLS
NVIDIA_MAX_CONCURRENCY=2                   # hosted trial keys allow ~40 requests/min
```

Guarantees:

- **No calls without the gate.** `NvidiaLLMProvider` raises `ConfigurationError` unless
  `ALLOW_NVIDIA_CALLS=true` and a key are present. Both test trees force the gate off and drop
  the key (`tests/conftest.py`, `apps/api/tests/conftest.py`); unit tests use an in-process
  `httpx.MockTransport`. `make test-nvidia` runs the single live check on purpose.
- **Not the AWS runtime.** `Settings.validate_for_environment()` rejects `LLM_PROVIDER=nvidia`
  when `APP_ENV=aws`; the Terraform `compute` module hard-codes `LLM_PROVIDER=bedrock`.
- **Same resilience.** The provider raises `ProviderError(retryable=…)` for 429/5xx and
  `ProviderTimeoutError` on timeouts, so `harden()` applies the same deadline + retry policy.
- **Usage is real.** Token counts come from the response `usage`; a stream that omits it falls
  back to the tokenizer estimate. Cost shows as $0.00 for catalog models on developer credits
  (`observability/pricing.py`); change the price table if the key is on a paid plan.

Rate limits: keep `NVIDIA_MAX_CONCURRENCY` small for the 315-question evaluation; 429s are
retried with backoff, and the run resumes rather than aborting.
