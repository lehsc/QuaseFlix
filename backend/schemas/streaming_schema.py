from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlaybackTrackSchema(BaseModel):
    language: str


class PlaybackSessionSchema(BaseModel):
    media_id: int
    episode_id: int | None
    title: str
    episode_title: str | None
    content_type: Literal["movie", "episode"]
    stream_url: str
    stream_type: str
    adaptive: bool
    duration_seconds: int
    resume_position_seconds: float
    completed: bool
    audio_tracks: list[PlaybackTrackSchema] = Field(default_factory=list)
    subtitle_tracks: list[PlaybackTrackSchema] = Field(default_factory=list)
    selected_audio: str | None = None
    selected_subtitle: str | None = None


class PlaybackProgressWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    position_seconds: float = Field(ge=0)
    audio_language: str | None = Field(default=None, min_length=1, max_length=100)
    subtitle_language: str | None = Field(default=None, min_length=1, max_length=100)


class PlaybackProgressSchema(BaseModel):
    position_seconds: float
    completed: bool
    audio_language: str | None
    subtitle_language: str | None
