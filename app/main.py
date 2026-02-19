from sqlite3 import Connection

import uvicorn
from fastapi import FastAPI

from app.core.config import Settings
from app.api.routers import debug, areas, rent, postcode_map

def create_app() -> FastAPI:
    app = FastAPI(
        title="Housing API",
        version="1.0",
        debug=True,
    )
    app.include_router(debug.router, tags=["debug"])
    app.include_router(areas.router, prefix="/areas", tags=["areas"])
    app.include_router(postcode_map.router, prefix="/postcode_map", tags=["postcode_map"])

    # app.include_router(rent.router, prefix="/rent", tags=["rent"])
    return app




if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(app=create_app(), host=settings.HOST, port=settings.PORT,)

    app = create_app()