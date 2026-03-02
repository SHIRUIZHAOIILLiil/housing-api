import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.api.routers import router_areas, router_rent, router_postcode_map, router_sales_official, router_rent_user, router_sales_user
from app.schemas.errors import AppError

def create_app() -> FastAPI:
    app = FastAPI(
        title="Housing API",
        version="1.0",
        debug=True,
    )

    @app.exception_handler(AppError)
    def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router_areas.router, prefix="/areas", tags=["areas"])
    app.include_router(router_postcode_map.router, prefix="/postcode_map", tags=["postcode_map"])
    app.include_router(router_rent.router, prefix="/rent_stats_official", tags=["rent_stats_official"])
    app.include_router(router_sales_official.router, prefix="/sales_official", tags=["sales_official"])
    app.include_router(router_rent_user.router, prefix="/rent_user", tags=["rent_user"])
    app.include_router(router_sales_user.router, prefix="/user-sales-transactions", tags=["user_sales_transactions"])
    return app

app = create_app()


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(app=create_app(), host=settings.HOST, port=settings.PORT,)

    app = create_app()