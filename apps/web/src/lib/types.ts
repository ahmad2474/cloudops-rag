/** Mirrors the FastAPI response models (docs/api.md). Keep in sync by hand; small on purpose. */

export type Role = "developer" | "platform-engineer" | "security-admin";
export type Strategy = "vector" | "bm25" | "hybrid_rrf" | "hybrid_weighted";
export type ContextMode = "parent" | "child" | "child_window";
export type AnswerStatus = "answered" | "abstained" | "no_authorized_evidence" | "blocked";

export interface TrailStep {
  stage: string;
  count: number;
  latency_ms: number;
  detail: Record<string, unknown>;
}

export interface Citation {
  sid: string;
  document_id: string;
  parent_id: string;
  title: string;
  section: string;
  source_url: string | null;
  document_type: string;
  version: string | null;
  updated_at: string;
  excerpt: string;
  content: string;
  token_count: number;
}

export interface Conflict {
  kind: "version" | "deprecated" | "stale";
  sids: string[];
  preferred: string;
  note: string;
}

export interface Evidence {
  score: number;
  label: "high" | "medium" | "low" | "none";
  signals: Record<string, number>;
}

export interface Usage {
  model: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
}

export interface QueryPlan {
  original: string;
  query: string;
  subqueries: string[];
  version_hint: string | null;
  incident_ids: string[];
  document_type_hint: string | null;
  stripped_injection: boolean;
}

export interface AnswerResponse {
  query: string;
  status: AnswerStatus;
  answer: string;
  citations: Citation[];
  sources: Citation[];
  dropped_citations: string[];
  guard_reasons: string[];
  conflicts: Conflict[];
  evidence: Evidence | null;
  query_plan: QueryPlan;
  trail: TrailStep[];
  usage: Usage | null;
  latency_ms: Record<string, number>;
}

export interface QueryFilters {
  document_types?: string[];
  environments?: string[];
  version?: string;
  sources?: string[];
  include_deprecated?: boolean;
}

export interface AskRequest {
  question: string;
  filters?: QueryFilters;
  strategy?: Strategy | null;
  rerank?: boolean | null;
  context_mode?: ContextMode | null;
}

export interface Chunk {
  chunk_id: string;
  parent_id: string;
  document_id: string;
  position: number;
  title: string;
  source: string;
  source_url: string | null;
  document_type: string;
  version: string | null;
  environment: string;
  permissions: Role[];
  status: string;
  updated_at: string;
  section_path: string[];
  content: string;
  token_count: number;
}

export interface SearchResponse {
  query: string;
  hits: { score: number; chunk: Chunk }[];
  trail: TrailStep[];
}

export interface IncidentMeta {
  incident_id: string;
  severity: "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4";
  detected_at: string;
  resolved_at: string | null;
  services: string[];
  root_cause_category: string;
}

export interface DocumentMetadata {
  document_id: string;
  title: string;
  source: "acme" | "aws" | "kubernetes" | "terraform";
  source_url: string | null;
  document_type: string;
  version: string | null;
  environment: string;
  permissions: Role[];
  status: string;
  supersedes: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
  related: string[];
  license: string | null;
  incident: IncidentMeta | null;
}

export interface DocumentSummary {
  metadata: DocumentMetadata;
  word_count: number;
  fetched: boolean;
}

export interface DocumentDetail extends DocumentSummary {
  body: string;
  related_titles: Record<string, string>;
}

export interface CatalogueStats {
  total: number;
  visible: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
  tags: Record<string, number>;
}

export interface MetricBlock {
  n: number;
  recall_at_5: number;
  recall_at_10: number;
  mrr: number;
  ndcg_at_10: number;
  acl_violations: number;
  abstention_accuracy: number | null;
  citation_precision: number | null;
  citation_recall: number | null;
  citation_violations: number | null;
  content_checks_pass_rate: number | null;
  injection_success_rate: number | null;
  faithfulness: number | null;
}

export interface ReportSummary {
  name: string;
  generated_at: string;
  dataset_version: string;
  strategy: string;
  providers: Record<string, string>;
  generation: boolean;
  summary: MetricBlock;
  by_category: Record<string, MetricBlock>;
  latency_ms: Record<string, number>;
  cost: Record<string, number>;
  context: Record<string, number>;
}

export interface RequestRecord {
  request_id: string;
  timestamp: string;
  user: string;
  roles: string[];
  query: string;
  strategy: string;
  answer_status: string;
  retrieval_count: number;
  bm25_results: number;
  vector_results: number;
  fusion_results: number;
  reranker_results: number;
  final_sources: number;
  citations: number;
  conflicts: number;
  evidence: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  retrieval_latency_ms: number;
  reranker_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
  abstained: boolean;
  blocked: boolean;
}

export interface SystemSummary {
  ledger: Record<string, number>;
  config: Record<string, string | boolean>;
}

export interface ReadyResponse {
  status: "ready" | "degraded";
  search: boolean;
  index: Record<string, number | null>;
  providers: Record<string, string>;
}

export interface Principal {
  username: string;
  roles: Role[];
}
