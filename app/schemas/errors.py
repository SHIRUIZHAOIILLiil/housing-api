from pydantic import BaseModel, Field

class ErrorOut(BaseModel):
    detail: str = Field(
        ...,
        description="Human-readable error message describing why the request failed.",
        examples=["Area not found"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Area not found",
            }
        }
    }

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

class ConflictError(AppError):
    status_code = 409

class UnauthorizedError(AppError):
    status_code = 401
