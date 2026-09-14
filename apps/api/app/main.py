from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.evaluation import router as evaluation_router
from app.api.health import router as health_router
from app.api.system import router as system_router
from app.dependencies import AppState
from app.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.problems import install_error_handlers
from cloudops_rag import __version__
from cloudops_rag.config import Settings, load_settings
from cloudops_rag.errors import ConfigurationError
from cloudops_rag.logging import configure_logging, get_logger
from cloudops_rag.observability.records import RequestLedger
from cloudops_rag.observability.resilience import TokenBucket
from cloudops_rag.providers.registry import build_providers
from cloudops_rag.providers.resilient import harden
from cloudops_rag.security import TokenService, UserStore

log = get_logger(__name__)


def create_app(settings: Settings | None = None, *, use_stub_search: bool = False) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        problems = settings.validate_for_environment()
        if problems:
            raise ConfigurationError("; ".join(problems))
        raw_providers = build_providers(settings, use_stub_search=use_stub_search)
        providers = harden(raw_providers, settings)
        app.state.ctx = AppState(
            settings=settings,
            providers=providers,
            raw_providers=raw_providers,
            users=UserStore.from_json(settings.auth_users),
            tokens=TokenService(settings.auth_secret, ttl_seconds=settings.auth_token_ttl_seconds),
            ledger=RequestLedger(settings.request_ledger_size),
            limiter=TokenBucket(settings.rate_limit_rpm),
        )
        log.info(
            "startup",
            app_env=settings.app_env,
            llm=f"{settings.llm_provider}:{settings.llm_model}",
            embedding=f"{settings.embedding_provider}:{settings.embedding_model}",
            search=settings.search_provider,
            retrieval=settings.retrieval_strategy,
            rerank=settings.rerank_enabled,
            auth_users=len(app.state.ctx.users),
            dev_role_header=settings.role_header_enabled,
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Acme-Role", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(ask_router)
    app.include_router(system_router)
    app.include_router(documents_router)
    app.include_router(evaluation_router)
    return app


app = create_app()
