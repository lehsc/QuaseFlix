import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.exceptions import MediaNotFoundError
from backend.routers.auth import get_current_account
from backend.schemas.catalog_schema import CatalogSchema, GenreSchema, MediaDetailSchema, MediaType
from backend.services import catalog_services

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/catalog", tags=["Catalog"],
                   dependencies=[Depends(get_current_account)])


@router.get("/genres", response_model=list[GenreSchema])
def api_list_genres():
    try:
        return catalog_services.list_genres()
    except Exception:
        logger.exception("Unable to list catalog genres.")
        raise HTTPException(status_code=500, detail="Unable to list genres.")


@router.get("", response_model=CatalogSchema)
def api_list_catalog(
    q: str = Query(default="", max_length=200),
    media_type: MediaType | None = None,
    genre_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return catalog_services.list_catalog(q, media_type, genre_id, limit, offset)
    except Exception:
        logger.exception("Unable to list catalog.")
        raise HTTPException(status_code=500, detail="Unable to list catalog.")


@router.get("/{media_id}", response_model=MediaDetailSchema)
def api_get_media(media_id: int = Path(gt=0)):
    try:
        return catalog_services.get_media(media_id)
    except MediaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception:
        logger.exception("Unable to retrieve media details.")
        raise HTTPException(status_code=500, detail="Unable to retrieve media details.")
