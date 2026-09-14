from dataclasses import dataclass

from fastapi import Request

from cloudops_rag.config import Settings
from cloudops_rag.providers.registry import Providers


@dataclass(frozen=True)
class AppState:
    settings: Settings
    providers: Providers


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.ctx
    return state
