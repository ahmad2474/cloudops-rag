"""Evaluation subsystem (spec §19-21): dataset schema, metrics, runner."""

from cloudops_rag.evaluation.dataset import Category, EvalDataset, EvalItem, load_dataset
from cloudops_rag.evaluation.metrics import mrr, ndcg_at_k, recall_at_k

__all__ = [
    "Category",
    "EvalDataset",
    "EvalItem",
    "load_dataset",
    "mrr",
    "ndcg_at_k",
    "recall_at_k",
]
