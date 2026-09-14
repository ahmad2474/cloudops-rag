from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.dependencies import AppState
from app.middleware import RequestContextMiddleware
from cloudops_rag import __version__
from cloudops_rag.config import Settings, load_settings
from cloudops_rag.logging import configure_logging, get_logger
from cloudops_rag.providers.registry import build_providers

log = get_logger(__name__)


def create_app(settings: Settings | None = None, *, use_stub_search: bool = False) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        providers = build_providers(settings, use_stub_search=use_stub_search)
        app.state.ctx = AppState(settings=settings, providers=providers)
        log.info(
            "startup",
            app_env=settings.app_env,
            llm_provider=settings.llm_provider,
            embedding_provider=settings.embedding_provider,
            search_provider=settings.search_provider,
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
    return app


app = create_app()
