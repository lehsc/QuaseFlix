import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials
from psycopg.errors import UndefinedTable, UndefinedColumn
from backend.routers.auth import get_current_account, _bearer_scheme
from backend.models.authenticated_account import AuthenticatedAccount
from backend.models.profile import SelectedProfile
from backend.schemas.profile_schema import ProfileWrite, OwnerConfirmation
from backend.services import profile_services as service

class ProfileRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except (UndefinedTable, UndefinedColumn):
                logging.getLogger(__name__).exception(
                    'Profile database is not ready. Apply backend/database/migrations/004_profiles.sql.'
                )
                # A handled response retains CORS headers. Unhandled database
                # errors otherwise appear as an opaque "Failed to fetch".
                raise HTTPException(
                    503, 'Os perfis estão indisponíveis até a atualização do sistema. Contate o responsável.'
                )

        return handle


router = APIRouter(tags=['Profiles'], route_class=ProfileRoute)


def profile_identity(account: AuthenticatedAccount = Depends(get_current_account),
                     credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)):
    return account.id, credentials.credentials


@router.get('/api/genres')
def genres(account: AuthenticatedAccount = Depends(get_current_account)):
    return service.list_genres()


@router.get('/api/profiles')
def profiles(identity=Depends(profile_identity)):
    return service.list_profiles(identity[0])


@router.get('/api/profiles/current')
def current(identity=Depends(profile_identity)):
    return service.current_selection(*identity)


def require_selected_profile(identity=Depends(profile_identity)) -> SelectedProfile:
    selection = service.current_selection(*identity)
    if selection['profile'] is None:
        raise HTTPException(409, 'Select a profile first.')
    return SelectedProfile(**selection['profile'])


@router.post('/api/profiles', status_code=201)
def create(data: ProfileWrite, identity=Depends(profile_identity)):
    return service.write_profile(*identity, data)


@router.put('/api/profiles/{profile_id}')
def update(profile_id: int, data: ProfileWrite, identity=Depends(profile_identity)):
    return service.write_profile(*identity, data, profile_id)


@router.delete('/api/profiles/{profile_id}', status_code=204)
def delete(profile_id: int, data: OwnerConfirmation, identity=Depends(profile_identity)):
    service.delete_profile(*identity, profile_id, data.password)
    return Response(status_code=204)


@router.post('/api/profiles/{profile_id}/select')
def select(profile_id: int, data: OwnerConfirmation, identity=Depends(profile_identity)):
    return service.select_profile(*identity, profile_id, data.password)
