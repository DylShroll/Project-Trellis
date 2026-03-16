from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.garden.router import router as garden_router
from app.modules.journal.router import router as journal_router
from app.modules.notifications.router import router as notifications_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trellis",
        description="Cultivate Curiosity. Nurture Connection.",
        version="0.1.0",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(garden_router)
    app.include_router(journal_router)
    app.include_router(notifications_router)

    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        pass  # static dir may not exist in test environments

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
