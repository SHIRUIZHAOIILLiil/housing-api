import os


class Config:
    DEBUG = True
    SECRET_KEY = "development key"
    HOST = os.getenv('HOST')
    PORT = int(os.getenv("FLASK_PORT"))