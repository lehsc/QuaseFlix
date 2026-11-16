from dataclasses import dataclass


@dataclass(frozen=True)
class SelectedProfile:
    """Trusted context loaded from the database, never from browser claims."""
    id: int
    account_id: int
    name: str
    is_kids: bool
    restricted: bool
    genre_ids: tuple[int, ...]
