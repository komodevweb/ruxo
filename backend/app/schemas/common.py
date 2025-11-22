from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    message: str = "Success"
    success: bool = True

class ErrorResponse(BaseModel):
    detail: str

