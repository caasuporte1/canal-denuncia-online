from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.routes.acompanhar import router as acompanhar_router
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.empresa import router as empresa_router
from app.routes.health import router as health_router
from app.routes.public import router as public_router

configure_logging()

app = FastAPI()
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status_code=429)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Canal de Denuncia Online", "status": "ok"}


app.include_router(health_router)
app.include_router(acompanhar_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(empresa_router)
app.include_router(public_router)
