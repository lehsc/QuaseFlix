import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.exceptions import EpisodeRequiredError, MediaNotFoundError, PlaybackOptionError
from backend.models.profile import SelectedProfile
from backend.routers.auth import get_current_account
from backend.routers.profiles import require_selected_profile
from backend.schemas.streaming_schema import (
    PlaybackProgressSchema,
    PlaybackProgressWrite,
    PlaybackSessionSchema,
)
from backend.services import streaming_services

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/streaming",
    tags=["Streaming"],
    dependencies=[Depends(get_current_account)],
)


@router.get("/{media_id}", response_model=PlaybackSessionSchema)
def api_get_playback(
    media_id: int = Path(gt=0),
    episode_id: int | None = Query(default=None, gt=0),
    profile: SelectedProfile = Depends(require_selected_profile),
):
    try:
        return streaming_services.get_playback(
            profile.id, media_id, episode_id, restricted=profile.restricted)
    except HTTPException:
        raise
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except EpisodeRequiredError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except Exception:
        logger.exception("Unable to prepare playback.")
        raise HTTPException(status_code=500, detail="Unable to prepare playback.")


@router.put("/{media_id}/progress", response_model=PlaybackProgressSchema)
def api_save_progress(
    payload: PlaybackProgressWrite,
    media_id: int = Path(gt=0),
    episode_id: int | None = Query(default=None, gt=0),
    profile: SelectedProfile = Depends(require_selected_profile),
):
    try:
        # Resolve and authorize every write; a stale page cannot save progress
        # for a title that the currently selected profile cannot see.
        return streaming_services.save_progress(
            profile.id, media_id, episode_id, payload.position_seconds,
            payload.audio_language, payload.subtitle_language,
            restricted=profile.restricted,
        )
    except HTTPException:
        raise
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except EpisodeRequiredError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except PlaybackOptionError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except Exception:
        logger.exception("Unable to save playback progress.")
        raise HTTPException(status_code=500, detail="Unable to save playback progress.")
