from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.ask import router as ask_router
from app.api.health import router as health_router
from app.dependencies import AppState
from app.middleware import RequestContextMiddleware
from cloudops_rag import __version__
from cloudops_rag.config import Settings, load_settings
from cloudops_rag.generation import AnswerService
from cloudops_rag.logging import configure_logging, get_logger
from cloudops_rag.providers.registry import build_providers
from cloudops_rag.retrieval import VectorRetriever

log = get_logger(__name__)


def create_app(settings: Settings | None = None, *, use_stub_search: bool = False) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        providers = build_providers(settings, use_stub_search=use_stub_search)
        retriever = VectorRetriever(
            providers.embedding,
            providers.search,
            candidates=settings.retrieval_candidates,
            top_k=settings.retrieval_top_k,
        )
        answers = AnswerService(
            retriever,
            providers.llm,
            context_token_budget=settings.context_token_budget,
            max_tokens=settings.llm_max_tokens,
        )
        app.state.ctx = AppState(
            settings=settings, providers=providers, retriever=retriever, answers=answers
        )
        log.info(
            "startup",
            app_env=settings.app_env,
            llm=f"{settings.llm_provider}:{settings.llm_model}",
            embedding=f"{settings.embedding_provider}:{settings.embedding_model}",
            search=settings.search_provider,
            allow_aws_calls=settings.allow_aws_calls,
        )
        try:
            yield
        finally:
            await providers.search.close()
            log.info("shutdown")

    app = FastAPI(
        title="CloudOps Knowledge Assistant API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "aws" else None,
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    app.include_router(ask_router)
    return app


app = create_app()
