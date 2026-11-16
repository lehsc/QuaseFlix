from pydantic import BaseModel, Field


# Schema for logging in (incoming request data)
class LoginSchema(BaseModel):
    email: str = Field(min_length = 1, max_length = 255)
    password: str = Field(min_length = 1, max_length = 128)
