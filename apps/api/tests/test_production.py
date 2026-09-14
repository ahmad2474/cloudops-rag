import json

from httpx import AsyncClient

from app.main import create_app
from cloudops_rag.config import Settings
from cloudops_rag.testing import test_users_json

_USERS = test_users_json()


async def test_ready_becomes_ready_once_indexed(seeded_client: AsyncClient) -> None:
    r = await seeded_client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready" and r.json()["index"]["chunks"] > 0


async def test_problem_json_for_domain_errors_and_validation(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post("/ask", json={"question": "x"})  # too short → 422 (FastAPI)
    assert r.status_code == 422
    r2 = await seeded_client.post(
        "/ask", json={"question": "hello there"}, headers={"X-Acme-Role": "root"}
    )
    assert r2.status_code == 400


async def test_body_size_limit_returns_413_problem() -> None:
    app = create_app(
        Settings(app_env="test", log_level="WARNING", auth_users=_USERS, max_request_bytes=2048),
        use_stub_search=True,
    )
    from httpx import ASGITransport

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/ask", json={"question": "x" * 4000})
            assert r.status_code == 413
            assert r.headers["content-type"].startswith("application/problem+json")
            assert r.json()["title"] == "Payload too large"


async def test_rate_limit_returns_429_with_retry_after() -> None:
    app = create_app(
        Settings(app_env="test", log_level="WARNING", auth_users=_USERS, rate_limit_rpm=3),
        use_stub_search=True,
    )
    from httpx import ASGITransport

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            codes = [
                (await c.post("/search", json={"query": "pods pending"})).status_code
                for _ in range(4)
            ]
            assert codes[:3] == [200, 200, 200] and codes[3] == 429
            r = await c.post("/search", json={"query": "pods pending"})
            assert r.headers.get("Retry-After", "").isdigit()
            assert r.json()["status"] == 429 and r.json()["request_id"]
            # a different principal has its own bucket
            ok = await c.post(
                "/search", json={"query": "pods pending"}, headers={"X-Acme-Role": "security-admin"}
            )
            assert ok.status_code == 200


async def test_ask_stream_emits_retrieval_deltas_and_validated_done(
    seeded_client: AsyncClient,
) -> None:
    async with seeded_client.stream(
        "POST", "/ask/stream", json={"question": "Why are pods Pending with no IP address?"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        events = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    kinds = [e["event"] for e in events]
    assert kinds[0] == "retrieval" and kinds[-1] == "done" and "delta" in kinds
    assert events[0]["sources"] and events[0]["trail"]
    done = events[-1]["response"]
    assert done["status"] == "answered" and done["citations"]
    streamed = "".join(e["text"] for e in events if e["event"] == "delta")
    assert "[S1]" in streamed


async def test_system_endpoints_record_requests_and_scope_by_role(
    seeded_client: AsyncClient,
) -> None:
    await seeded_client.post("/ask", json={"question": "Why are pods Pending with no IP address?"})
    await seeded_client.post(
        "/ask",
        json={"question": "max_connections reserved slots"},
        headers={"X-Acme-Role": "security-admin"},
    )
    dev = await seeded_client.get("/system/requests")
    assert dev.status_code == 200
    assert {r["user"] for r in dev.json()} == {"dev:developer"}
    rec = dev.json()[0]
    assert rec["answer_status"] == "answered" and rec["vector_results"] > 0
    assert rec["retrieval_latency_ms"] >= 0 and rec["citations"] >= 1
    admin = await seeded_client.get("/system/requests", headers={"X-Acme-Role": "security-admin"})
    assert len(admin.json()) == 2
    summary = await seeded_client.get("/system/summary")
    s = summary.json()["ledger"]
    assert s["requests"] == 2 and s["answered"] == 2 and "p95_latency_ms" in s
