import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pathlib import Path

from app.core import Settings, RequestLoggingMiddleware, setup_logging
from app.api.routers import router_areas, router_rent, router_postcode_map, router_sales_official, router_rent_user, router_sales_user, router_auth
from app.schemas.errors import AppError

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

def create_app() -> FastAPI:
    app = FastAPI(
        title="Housing API",
        version="2.0",
        debug=True,
    )


    @app.exception_handler(AppError)
    def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    setup_logging()
    app.add_middleware(RequestLoggingMiddleware)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(STATIC_DIR / "index.html")
    app.include_router(router_areas.router, prefix="/areas", tags=["areas"])
    app.include_router(router_postcode_map.router, prefix="/postcode_map", tags=["postcode_map"])
    app.include_router(router_rent.router, prefix="/rent_stats_official", tags=["rent_stats_official"])
    app.include_router(router_sales_official.router, prefix="/sales_official", tags=["sales_official"])
    app.include_router(router_rent_user.router, prefix="/rent_user", tags=["rent_user"])
    app.include_router(router_sales_user.router, prefix="/user-sales-transactions", tags=["user_sales_transactions"])
    app.include_router(router_auth.router, prefix="/auth", tags=["authority"])
    return app

app = create_app()


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(app=create_app(), host=settings.HOST, port=settings.PORT,)

    app = create_app()