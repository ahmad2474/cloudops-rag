"""Evaluation reports for the dashboard — read from evaluation/reports/*.json, never computed."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.dependencies import Who
from cloudops_rag.evaluation.report import EvalReport, MetricBlock

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
REPORTS = Path(__file__).resolve().parents[4] / "evaluation" / "reports"


class ReportSummary(BaseModel):
    name: str
    generated_at: str
    dataset_version: str
    strategy: str
    providers: dict[str, str]
    generation: bool
    summary: MetricBlock
    by_category: dict[str, MetricBlock]
    latency_ms: dict[str, float]
    cost: dict[str, float]
    context: dict[str, float]


def _load(path: Path) -> ReportSummary:
    r = EvalReport.model_validate_json(path.read_text())
    return ReportSummary(name=path.stem, **r.model_dump(exclude={"items"}))


@router.get("/reports", response_model=list[ReportSummary])
async def list_reports(who: Who) -> list[ReportSummary]:
    if not REPORTS.exists():
        return []
    paths = sorted(REPORTS.glob("*.json"))
    out = await asyncio.gather(*(asyncio.to_thread(_load, p) for p in paths))
    return sorted(out, key=lambda r: r.generated_at, reverse=True)


@router.get("/reports/{name}")
async def get_report(name: str, who: Who) -> dict[str, object]:
    path = REPORTS / f"{name}.json"
    if not path.is_file() or path.parent != REPORTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")
    data: dict[str, object] = json.loads(await asyncio.to_thread(path.read_text))
    return data
