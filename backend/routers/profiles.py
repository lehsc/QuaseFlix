from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from backend.routers.auth import get_current_account, _bearer_scheme
from backend.models.authenticated_account import AuthenticatedAccount
from backend.models.profile import SelectedProfile
from backend.schemas.profile_schema import ProfileWrite, OwnerConfirmation
from backend.services import profile_services as service

router = APIRouter(tags=['Profiles'])


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
