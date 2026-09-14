"""Security: identity, tokens, and the role → ACL boundary.

Authorization itself lives in ``SearchFilters.roles`` (enforced inside every search request).
This package only establishes *who* the caller is and *which roles* they carry.
"""

from cloudops_rag.security.auth import (
    AuthError,
    Principal,
    TokenService,
    UserStore,
    hash_password,
)

__all__ = ["AuthError", "Principal", "TokenService", "UserStore", "hash_password"]
