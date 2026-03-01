from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from server.api import router as api_router

# Project Imports
from server.config import SCREENSHOT_DIR, get_settings
from server.dependencies import api_key_auth

settings = get_settings()


app = FastAPI(
    title="Backend Service for QA Engineer Bot",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOT_DIR)), name="screenshots")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        dict.fromkeys(
            [
                *settings.cors_allowed_origins,
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Customer-Session-Id",
        settings.api_auth_key_name,
    ],
)

if settings.trusted_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(
    api_router,
    prefix="/api",
    dependencies=[Depends(api_key_auth)],
)


@app.get("/", tags=["meta"], status_code=200)
async def root() -> dict[str, str]:
    return {"service": "Backend Service QA Engineer Bot", "status": "ok"}
