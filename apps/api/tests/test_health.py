from httpx import AsyncClient

from cloudops_rag import __version__


async def test_health_reports_version(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


async def test_ready_with_stub_search_is_ready(client: AsyncClient) -> None:
    r = await client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["search"] is True
    assert body["providers"]["llm"] == "stub:stub-model"


async def test_request_id_is_generated_and_echoed(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.headers["X-Request-ID"].startswith("req_")


async def test_request_id_is_propagated_when_supplied(client: AsyncClient) -> None:
    r = await client.get("/health", headers={"X-Request-ID": "req_from_caller"})
    assert r.headers["X-Request-ID"] == "req_from_caller"
