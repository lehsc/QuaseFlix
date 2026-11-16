from pydantic import BaseModel, Field, field_validator


class OwnerConfirmation(BaseModel):
    password: str | None = Field(default=None, max_length=128)


class ProfileWrite(OwnerConfirmation):
    name: str = Field(min_length=1, max_length=100)
    is_kids: bool = False
    genre_ids: list[int] = Field(default_factory=list, max_length=50)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError('Enter a non-empty profile name without control characters.')
        return value

    @field_validator('genre_ids')
    @classmethod
    def clean_genres(cls, value):
        if any(genre_id <= 0 for genre_id in value):
            raise ValueError('Genre IDs must be positive.')
        return sorted(set(value))
