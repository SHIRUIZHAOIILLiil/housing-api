import os


class Config:
    DEBUG = True
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SECRET_KEY = "development key"
    HOST = os.getenv('HOST')
    PORT = int(os.getenv("FLASK_PORT"))
    DATAPATH = os.getenv('DATAPATH')
    NAME = ['NSPL_NOV_2025_UK.csv',
            'pp-complete-2020.csv',
            'pp-complete-2021.csv',
            'pp-complete-2022.csv',
            'pp-complete-2023.csv',
            'pp-complete-2024.csv',
            'pp-complete-2025.csv',
            'priceindexofprivaterentsukmonthlypricestatistics.xlsx']
    DATABASE = os.path.join(BASE_DIR, "data", "housing.db")