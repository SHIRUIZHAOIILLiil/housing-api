from sqlite3 import Connection

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.api.routers import debug, router_areas, router_rent, router_postcode_map, router_sales_official

def create_app() -> FastAPI:
    app = FastAPI(
        title="Housing API",
        version="1.0",
        debug=True,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Change the FastAPI default 422 to 400 and compress the information into a string (more in line with Class ErrorOut).
        msg = "; ".join([f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()])
        return JSONResponse(status_code=400, content={"detail": msg})

    app.include_router(debug.router, tags=["debug"])
    app.include_router(router_areas.router, prefix="/areas", tags=["areas"])
    app.include_router(router_postcode_map.router, prefix="/postcode_map", tags=["postcode_map"])
    app.include_router(router_rent.router, prefix="/rent_stats_official", tags=["rent_stats_official"])
    app.include_router(router_sales_official.router, prefix="/sales_official", tags=["sales_official"])
    return app




if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(app=create_app(), host=settings.HOST, port=settings.PORT,)

    app = create_app()