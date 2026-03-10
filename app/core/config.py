from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict



BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):

    JWT_SECRET: str = "dev-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore',
    )

    DEBUG: bool = True
    SECRET_KEY: str = "development key"

    HOST: str = "127.0.0.1"
    PORT: int = 4444
    DATAPATH: str = "data"
    DATABASE: str = os.path.join(BASE_DIR, "data", "housing.db")
    DATABASE_DEMO: str = os.path.join(BASE_DIR, "data", "housing_demo.db")

    NAME: list[str] = ['NSPL_NOV_2025_UK.csv',
            'pp-complete-2020.csv',
            'pp-complete-2021.csv',
            'pp-complete-2022.csv',
            'pp-complete-2023.csv',
            'pp-complete-2024.csv',
            'pp-complete-2025.csv',
            'priceindexofprivaterentsukmonthlypricestatistics.xlsx']

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_SECRET: str = os.getenv("JWT_SECRET")

    @property
    def port(self):
        return self.PORT

    @property
    def base_dir(self):
        return str(BASE_DIR)

    @property
    def env_file(self):
        return str(ENV_FILE)

# class Config:
#     DEBUG = True
#     BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
#     ENV_FILE = os.path.join(BASE_DIR, ".env")
#     SECRET_KEY = "development key"
#     HOST = os.getenv('HOST')
#     PORT = int(os.getenv("FLASK_PORT"))
#     DATAPATH = os.getenv('DATAPATH')
#
#     DATABASE = os.path.join(BASE_DIR, "data", "housing.db")