"""Shared policy for future catalog, search, details and playback endpoints.

Call with a SelectedProfile loaded through require_selected_profile. Age rating
0 is Livre. Unclassified titles are unavailable to child profiles.
"""
from fastapi import HTTPException
from backend.models.profile import SelectedProfile


def is_allowed(profile: SelectedProfile, age_rating: int | None) -> bool:
    return not profile.restricted or (type(age_rating) is int and age_rating == 0)


def require_media_allowed(profile: SelectedProfile, age_rating: int | None):
    if not is_allowed(profile, age_rating):
        raise HTTPException(404, 'Title not available for this profile.')


def personalize(profile: SelectedProfile, titles: list[dict]) -> list[dict]:
    """Filter first, then prioritize preferred genres. Preserve order for ties.

No matching preferences returns the entire eligible collection, including the
full child-safe collection when no child title matches the selected genres.
    """
    eligible = [title for title in titles if is_allowed(profile, title.get('age_rating'))]
    preferences = set(profile.genre_ids)
    return sorted(eligible, key=lambda title: -len(preferences.intersection(title.get('genre_ids', []))))
