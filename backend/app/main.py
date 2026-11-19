import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analytics, auth, conversations, database, debug, query
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging

setup_logging()
log = logging.getLogger("intelliquery")
settings = get_settings()

if settings.is_production and settings.secret_key in ("change-me", "", "change-me-to-a-long-random-string"):
    raise RuntimeError("SECRET_KEY must be set to a long random value when APP_ENV=production.")

app = FastAPI(title="IntelliQuery API", version="1.0.0",
              description="AI-powered Text-to-SQL with an intelligent clarification engine.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    msgs = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse({"detail": "; ".join(msgs) or "Invalid request"}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)  # no internals leaked


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


for r in (auth.router, database.router, conversations.router, query.router, analytics.router, debug.router):
    app.include_router(r, prefix="/api")
