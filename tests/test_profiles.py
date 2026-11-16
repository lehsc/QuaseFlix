import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.profile import SelectedProfile
from backend.schemas.profile_schema import ProfileWrite
from backend.services.content_policy import is_allowed, personalize, require_media_allowed
from backend.security import create_access_token, decode_access_token


def context(restricted=True, genres=(1,)):
    return SelectedProfile(1, 1, 'Child', restricted, restricted, genres)


@pytest.mark.parametrize('name', ['', '  ', 'x'*101, 'Name\nName'])
def test_invalid_profile_names(name):
    with pytest.raises(ValidationError):
        ProfileWrite(name=name)


def test_name_and_preferences_normalized():
    data = ProfileWrite(name='  Principal  ', genre_ids=[3,1,3])
    assert data.name == 'Principal'
    assert data.genre_ids == [1,3]


@pytest.mark.parametrize('rating', [None,10,12,14,16,18,True,'0'])
def test_child_policy_rejects_unknown_or_non_livre(rating):
    assert not is_allowed(context(), rating)
    with pytest.raises(HTTPException) as error:
        require_media_allowed(context(), rating)
    assert error.value.status_code == 404


def test_preferences_never_override_child_filter():
    titles = [dict(id=1,age_rating=18,genre_ids=[1]),dict(id=2,age_rating=0,genre_ids=[2]),dict(id=3,age_rating=0,genre_ids=[1])]
    assert [t['id'] for t in personalize(context(),titles)] == [3,2]
    assert [t['id'] for t in personalize(context(genres=(99,)),titles)] == [2,3]
    assert [t['id'] for t in personalize(context(False,()),titles)] == [1,2,3]


def test_two_logins_in_same_second_have_independent_tokens():
    first, second = create_access_token(7, now=1000), create_access_token(7, now=1000)
    assert first != second
    assert decode_access_token(first, now=1000) == decode_access_token(second, now=1000) == 7


@pytest.mark.parametrize('method,path,body', [
    ('get','/api/profiles',None), ('get','/api/profiles/current',None), ('get','/api/genres',None),
    ('post','/api/profiles',{'name':'Test'}), ('put','/api/profiles/1',{'name':'Test'}),
    ('delete','/api/profiles/1',{}), ('post','/api/profiles/1/select',{})
])
def test_profiles_require_authentication(method,path,body):
    response = TestClient(app).request(method,path,**({'json':body} if body is not None else {}))
    assert response.status_code == 401
