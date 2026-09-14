from httpx import AsyncClient


async def test_documents_list_is_acl_filtered(seeded_client: AsyncClient) -> None:
    dev = await seeded_client.get("/documents", params={"document_type": "policy"})
    sec = await seeded_client.get(
        "/documents", params={"document_type": "policy"}, headers={"X-Acme-Role": "security-admin"}
    )
    dev_ids = {d["metadata"]["document_id"] for d in dev.json()}
    sec_ids = {d["metadata"]["document_id"] for d in sec.json()}
    assert "break-glass-procedure" not in dev_ids and "break-glass-procedure" in sec_ids
    assert "production-access" in dev_ids


async def test_incidents_carry_structured_block_and_detail_has_body(
    seeded_client: AsyncClient,
) -> None:
    r = await seeded_client.get("/documents", params={"document_type": "incident", "limit": 5})
    inc = r.json()
    assert len(inc) == 5 and inc[0]["metadata"]["incident"]["incident_id"].startswith("INC-")
    d = await seeded_client.get("/documents/inc-1042")
    body = d.json()
    assert body["metadata"]["incident"]["severity"] == "SEV-2"
    assert "# INC-1042" in body["body"] and "postmortem-inc-1042" in body["related_titles"]


async def test_restricted_document_is_404_for_unauthorized_role(seeded_client: AsyncClient) -> None:
    r = await seeded_client.get("/documents/break-glass-procedure")
    assert r.status_code == 404
    ok = await seeded_client.get(
        "/documents/break-glass-procedure", headers={"X-Acme-Role": "security-admin"}
    )
    assert ok.status_code == 200


async def test_stats_and_tags(seeded_client: AsyncClient) -> None:
    dev = (await seeded_client.get("/documents/stats")).json()
    assert dev["visible"] < dev["total"]
    s = (
        await seeded_client.get("/documents/stats", headers={"X-Acme-Role": "security-admin"})
    ).json()
    assert s["by_type"]["incident"] == 70 and s["visible"] == s["total"]
    assert "eks" in s["tags"]


async def test_evaluation_reports_endpoint_lists_or_is_empty(seeded_client: AsyncClient) -> None:
    r = await seeded_client.get("/evaluation/reports")
    assert r.status_code == 200 and isinstance(r.json(), list)
    missing = await seeded_client.get("/evaluation/reports/../etc/passwd")
    assert missing.status_code in (404, 422)
