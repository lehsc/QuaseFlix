"""Profile API and transaction tests against QUASEFLIX_TEST_DATABASE_URL."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import connection
from backend.security import create_access_token, hash_password
from backend.services.profile_services import current_selection, select_profile

pytestmark = pytest.mark.skipif(not os.environ.get('QUASEFLIX_TEST_DATABASE_URL'), reason='Disposable PostgreSQL test URL not supplied')
PASSWORD = 'StrongPass123'


@pytest.fixture
def account(monkeypatch):
    monkeypatch.setattr(connection, 'DATABASE_URL', os.environ['QUASEFLIX_TEST_DATABASE_URL'])
    with connection.get_db_connection() as conn:
        plan = conn.execute("INSERT INTO public.plan(name,price) VALUES ('Profile test',25.90) RETURNING id").fetchone()[0]
        ids=[]
        for _ in range(2):
            ids.append(conn.execute("""INSERT INTO public.account(email,password_hash,cpf,birth_date,address,plan_id)
                VALUES (%s,%s,%s,'2000-01-01','Test address',%s) RETURNING id""",
                (f'{uuid.uuid4().hex}@example.com',hash_password(PASSWORD),uuid.uuid4().hex[:14],plan)).fetchone()[0])
    token = create_access_token(ids[0])
    client = TestClient(app, headers={'Authorization':f'Bearer {token}'})
    yield ids, token, client
    with connection.get_db_connection() as conn:
        conn.execute('DELETE FROM public.account WHERE id=ANY(%s)',(ids,))
        conn.execute('DELETE FROM public.plan WHERE id=%s',(plan,))


def create(client, name='Child', **data):
    response = client.post('/api/profiles',json={'name':name,**data})
    assert response.status_code == 201, response.text
    return response.json()


def test_default_profile_and_genres(account):
    _, _, client = account
    profiles = client.get('/api/profiles').json()
    assert len(profiles) == 1
    assert profiles[0]['name'] == 'Principal'
    assert not profiles[0]['is_kids']
    assert profiles[0]['genre_ids'] == []
    assert len(client.get('/api/genres').json()) >= 8
    assert client.get('/api/profiles/current').json() == {'profile':None,'restricted':False}


def test_names_limits_and_last_profile(account):
    _, _, client = account
    initial = client.get('/api/profiles').json()[0]
    assert client.post('/api/profiles',json={'name':' PRINCIPAL '}).status_code == 409
    assert client.request('DELETE',f"/api/profiles/{initial['id']}",json={}).status_code == 409
    for name in ['Second','Third','Fourth']:
        create(client,name)
    assert client.post('/api/profiles',json={'name':'Fifth'}).status_code == 409
    second = client.get('/api/profiles').json()[1]
    assert client.put(f"/api/profiles/{second['id']}",json={'name':'Principal'}).status_code == 409


def test_ownership(account):
    ids, _, client = account
    other = TestClient(app,headers={'Authorization':f'Bearer {create_access_token(ids[1])}'})
    foreign = other.get('/api/profiles').json()[0]['id']
    assert client.put(f'/api/profiles/{foreign}',json={'name':'Intruder'}).status_code == 404
    assert client.request('DELETE',f'/api/profiles/{foreign}',json={}).status_code == 404
    assert client.post(f'/api/profiles/{foreign}/select',json={}).status_code == 404
    assert client.get('/api/profiles/current').json()['profile'] is None


def test_preferences_are_atomic_and_isolated(account):
    _, _, client = account
    genre = client.get('/api/genres').json()[0]['id']
    profile = create(client,'Cinema',genre_ids=[genre])
    other = client.get('/api/profiles').json()[0]
    assert other['genre_ids'] == []
    assert client.put(f"/api/profiles/{profile['id']}",json={'name':'Changed','genre_ids':[2147483647]}).status_code == 422
    unchanged = next(p for p in client.get('/api/profiles').json() if p['id']==profile['id'])
    assert unchanged['name'] == 'Cinema' and unchanged['genre_ids'] == [genre]
    cleared = client.put(f"/api/profiles/{profile['id']}",json={'name':'Cinema','genre_ids':[]})
    assert cleared.status_code == 200 and cleared.json()['genre_ids'] == []


def test_parental_protection_and_switching(account):
    _, _, client = account
    adult = client.get('/api/profiles').json()[0]
    child = create(client,is_kids=True)
    assert client.put(f"/api/profiles/{child['id']}",json={'name':'Child','is_kids':False}).status_code == 403
    assert client.post(f"/api/profiles/{child['id']}/select",json={}).status_code == 200
    assert client.post(f"/api/profiles/{adult['id']}/select",json={}).status_code == 403
    assert client.post(f"/api/profiles/{adult['id']}/select",json={'password':'wrong'}).status_code == 403
    assert client.post('/api/profiles',json={'name':'Bypass'}).status_code == 403
    assert client.put(f"/api/profiles/{adult['id']}",json={'name':'Bypass'}).status_code == 403
    assert client.request('DELETE',f"/api/profiles/{child['id']}",json={}).status_code == 403
    response = client.post(f"/api/profiles/{adult['id']}/select",json={'password':PASSWORD})
    assert response.status_code == 200 and not response.json()['restricted']
    response = client.put(f"/api/profiles/{child['id']}",json={'name':'Child','is_kids':False,'password':PASSWORD})
    assert response.status_code == 200


def test_child_selection_survives_deletion_from_other_session(account):
    ids, token, client = account
    adult = client.get('/api/profiles').json()[0]
    child = create(client,is_kids=True)
    client.post(f"/api/profiles/{child['id']}/select",json={})
    parent = TestClient(app,headers={'Authorization':f'Bearer {create_access_token(ids[0])}'})
    assert parent.request('DELETE',f"/api/profiles/{child['id']}",json={}).status_code == 204
    assert client.get('/api/profiles/current').json() == {'profile':None,'restricted':True}
    assert client.post(f"/api/profiles/{adult['id']}/select",json={}).status_code == 403
    assert client.post(f"/api/profiles/{adult['id']}/select",json={'password':PASSWORD}).status_code == 200


def test_external_child_setting_locks_existing_session(account):
    ids, _, client = account
    profile = client.get('/api/profiles').json()[0]
    client.post(f"/api/profiles/{profile['id']}/select",json={})
    parent = TestClient(app,headers={'Authorization':f'Bearer {create_access_token(ids[0])}'})
    parent.put(f"/api/profiles/{profile['id']}",json={'name':'Principal','is_kids':True})
    assert client.get('/api/profiles/current').json()['restricted']
    parent.put(f"/api/profiles/{profile['id']}",json={'name':'Principal','is_kids':False,'password':PASSWORD})
    assert client.get('/api/profiles/current').json()['restricted']
    assert client.post(f"/api/profiles/{profile['id']}/select",json={}).status_code == 403


def test_concurrent_creation_cannot_exceed_four(account):
    _, _, client = account
    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = list(pool.map(lambda i: client.post('/api/profiles',json={'name':f'Profile {i}'}).status_code, range(5)))
    assert statuses.count(201) == 3
    assert statuses.count(409) == 2
    assert len(client.get('/api/profiles').json()) == 4


def test_concurrent_deletion_keeps_one_profile(account):
    _, _, client = account
    create(client,'Second')
    ids = [p['id'] for p in client.get('/api/profiles').json()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda i: client.request('DELETE',f'/api/profiles/{i}',json={}).status_code, ids))
    assert sorted(statuses) == [204,409]
    assert len(client.get('/api/profiles').json()) == 1


def test_canceled_and_overdue_accounts_cannot_manage_profiles(account):
    ids, _, client = account
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.account SET status='CANCELED' WHERE id=%s",(ids[0],))
    assert client.get('/api/profiles').status_code == 403
    with connection.get_db_connection() as conn:
        conn.execute("UPDATE public.account SET status='ACTIVE' WHERE id=%s",(ids[0],))
        conn.execute("INSERT INTO public.subscription_invoice(account_id,period_start,amount,due_at) VALUES (%s,LOCALTIMESTAMP,25.90,LOCALTIMESTAMP - interval '1 second')",(ids[0],))
    assert client.get('/api/profiles').status_code == 402
