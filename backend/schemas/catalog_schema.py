from typing import Literal

from pydantic import BaseModel, Field

MediaType = Literal["movie", "series"]


class GenreSchema(BaseModel):
    id: int
    name: str


class MediaSummarySchema(BaseModel):
    id: int
    title: str
    media_type: MediaType
    release_year: int | None
    genres: list[str]
    age_rating: int | None = None


class EpisodeSchema(BaseModel):
    id: int
    episode_number: int
    title: str
    duration_minutes: int
    director: str | None


class SeasonSchema(BaseModel):
    id: int
    season_number: int
    title: str | None
    episodes: list[EpisodeSchema] = Field(default_factory=list)


class MediaDetailSchema(MediaSummarySchema):
    synopsis: str | None
    duration_minutes: int
    actors: list[str]
    directors: list[str]
    audio_languages: list[str]
    subtitle_languages: list[str]
    season_count: int
    episode_count: int
    seasons: list[SeasonSchema]


class CatalogSchema(BaseModel):
    items: list[MediaSummarySchema]
    total: int
    limit: int
    offset: int
    suggestions: list[MediaSummarySchema] = Field(default_factory=list)
