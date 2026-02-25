from pydantic import BaseModel

class ErrorOut(BaseModel):
    detail: str

class AppError(Exception):
    status_code: int = 400
    def __init__(self, message: str):
        self.message = message

class BadRequestError(AppError):
    status_code = 400

class NotFoundError(AppError):
    status_code = 404

class UnprocessableEntityError(AppError):
    status_code = 422