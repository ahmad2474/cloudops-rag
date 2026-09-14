from pydantic import BaseModel, ConfigDict, Field


class ItemResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    role: str
    should_abstain: bool
    ranked_documents: list[str]
    recall_at_5: float | None
    recall_at_10: float | None
    mrr: float | None
    ndcg_at_10: float | None
    acl_violation: bool
    retrieval_latency_ms: float
    context_tokens: int = 0
    # generation (None when retrieval-only)
    status: str | None = None
    cited_documents: list[str] = Field(default_factory=list)
    citation_precision: float | None = None
    citation_recall: float | None = None
    abstention_correct: bool | None = None
    citation_violation: bool | None = None
    content_checks_passed: bool | None = None
    injection_succeeded: bool | None = None
    faithfulness: float | None = None
    generation_latency_ms: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    answer_preview: str = ""


class MetricBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    n: int
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float
    acl_violations: int
    abstention_accuracy: float | None = None
    citation_precision: float | None = None
    citation_recall: float | None = None
    citation_violations: int | None = None
    content_checks_pass_rate: float | None = None
    injection_success_rate: float | None = None
    faithfulness: float | None = None


class EvalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: str
    dataset_version: str
    strategy: str
    providers: dict[str, str]
    generation: bool
    summary: MetricBlock
    by_category: dict[str, MetricBlock]
    latency_ms: dict[str, float]
    cost: dict[str, float]
    context: dict[str, float] = Field(default_factory=dict)
    items: list[ItemResult]
