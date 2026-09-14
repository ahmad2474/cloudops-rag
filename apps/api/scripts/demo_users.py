"""Print an AUTH_USERS JSON for the three demo roles. Usage:

uv run python apps/api/scripts_demo_users.py acme-demo >> .env   # (as AUTH_USERS=...)
"""

import json
import sys

from cloudops_rag.security import hash_password

pw = sys.argv[1] if len(sys.argv) > 1 else "acme-demo"
h = hash_password(pw)
users = {
    "dev": {"password_hash": h, "roles": ["developer"]},
    "pe": {"password_hash": h, "roles": ["platform-engineer"]},
    "sec": {"password_hash": h, "roles": ["security-admin"]},
}
print("AUTH_USERS=" + json.dumps(users, separators=(",", ":")))
