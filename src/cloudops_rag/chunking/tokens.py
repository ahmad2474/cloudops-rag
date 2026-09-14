"""Token counting. cl100k_base is a stable proxy for Titan/Nova tokenisation (±10%)."""

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc().encode(text, disallowed_special=()))
