"""Profile operations serialize on the account row, including selection changes."""
import hashlib
from dataclasses import asdict

from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from backend.database.connection import get_db_connection
from backend.models.profile import SelectedProfile
from backend.security import verify_password

MAX_PROFILES = 4


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def lock_account(cur, account_id):
    cur.execute('SELECT id,password_hash FROM public.account WHERE id=%s FOR UPDATE', (account_id,))
    account = cur.fetchone()
    if not account:
        raise HTTPException(401, 'Account not found.')
    return account


def owned_profile(cur, account_id, profile_id):
    cur.execute('SELECT id,account_id,name,is_kids FROM public.profile WHERE id=%s AND account_id=%s',
                (profile_id, account_id))
    profile = cur.fetchone()
    if not profile:
        raise HTTPException(404, 'Profile not found.')
    return profile


def session_state(cur, account_id, token):
    cur.execute('''SELECT s.profile_id, (s.parental_locked OR COALESCE(p.is_kids,false)) AS restricted
        FROM public.profile_session s LEFT JOIN public.profile p ON p.id=s.profile_id
        WHERE s.token_hash=%s AND s.account_id=%s''', (token_hash(token), account_id))
    return cur.fetchone()


def require_owner(account, password):
    if not password or not verify_password(password, account['password_hash']):
        raise HTTPException(403, 'Confirm the account owner password.')


def genre_ids(cur, profile_id):
    cur.execute('SELECT genre_id FROM public.profile_genre WHERE profile_id=%s ORDER BY genre_id', (profile_id,))
    return [row['genre_id'] for row in cur.fetchall()]


def list_profiles(account_id):
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT id,name,is_kids FROM public.profile WHERE account_id=%s ORDER BY id', (account_id,))
            profiles = cur.fetchall()
            for profile in profiles:
                profile['genre_ids'] = genre_ids(cur, profile['id'])
            return profiles


def list_genres():
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT id,name FROM public.genre ORDER BY name,id')
            return cur.fetchall()


def write_profile(account_id, token, data, profile_id=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                account = lock_account(cur, account_id)
                current = session_state(cur, account_id, token)
                existing = owned_profile(cur, account_id, profile_id) if profile_id is not None else None
                if (current and current['restricted']) or (existing and existing['is_kids'] and not data.is_kids):
                    require_owner(account, data.password)
                if data.genre_ids:
                    cur.execute('SELECT id FROM public.genre WHERE id=ANY(%s)', (data.genre_ids,))
                    if {row['id'] for row in cur.fetchall()} != set(data.genre_ids):
                        raise HTTPException(422, 'One or more genres do not exist.')
                if existing is None:
                    cur.execute('SELECT count(*) AS count FROM public.profile WHERE account_id=%s', (account_id,))
                    if cur.fetchone()['count'] >= MAX_PROFILES:
                        raise HTTPException(409, 'An account can have at most four profiles.')
                    cur.execute('INSERT INTO public.profile(account_id,name,is_kids) VALUES (%s,%s,%s) RETURNING id',
                                (account_id, data.name, data.is_kids))
                    profile_id = cur.fetchone()['id']
                else:
                    cur.execute('UPDATE public.profile SET name=%s,is_kids=%s WHERE id=%s',
                                (data.name, data.is_kids, profile_id))
                # Once a session enters child mode, deleting/renaming the profile
                # elsewhere cannot unlock it. Only an owner-approved selection can.
                if data.is_kids:
                    cur.execute('UPDATE public.profile_session SET parental_locked=true WHERE profile_id=%s', (profile_id,))
                cur.execute('DELETE FROM public.profile_genre WHERE profile_id=%s', (profile_id,))
                for genre_id in data.genre_ids:
                    cur.execute('INSERT INTO public.profile_genre(profile_id,genre_id) VALUES (%s,%s)', (profile_id, genre_id))
                return dict(id=profile_id, name=data.name, is_kids=data.is_kids, genre_ids=data.genre_ids)
    except UniqueViolation:
        raise HTTPException(409, 'This account already has a profile with that name.')


def delete_profile(account_id, token, profile_id, password=None):
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            account = lock_account(cur, account_id)
            owned_profile(cur, account_id, profile_id)
            current = session_state(cur, account_id, token)
            if current and current['restricted']:
                require_owner(account, password)
            cur.execute('SELECT count(*) AS count FROM public.profile WHERE account_id=%s', (account_id,))
            if cur.fetchone()['count'] <= 1:
                raise HTTPException(409, 'Keep at least one profile on the account.')
            cur.execute('DELETE FROM public.profile WHERE id=%s', (profile_id,))


def select_profile(account_id, token, profile_id, password=None):
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            account = lock_account(cur, account_id)
            profile = owned_profile(cur, account_id, profile_id)
            current = session_state(cur, account_id, token)
            if current and current['restricted'] and not profile['is_kids']:
                require_owner(account, password)
            cur.execute('''INSERT INTO public.profile_session(token_hash,account_id,profile_id,parental_locked)
                VALUES (%s,%s,%s,%s) ON CONFLICT(token_hash) DO UPDATE
                SET profile_id=EXCLUDED.profile_id,parental_locked=EXCLUDED.parental_locked''',
                (token_hash(token), account_id, profile_id, profile['is_kids']))
            return asdict(SelectedProfile(**profile, restricted=profile['is_kids'],
                                         genre_ids=tuple(genre_ids(cur, profile_id))))


def current_selection(account_id, token):
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Serialize with deletion and parental setting changes.
            lock_account(cur, account_id)
            state = session_state(cur, account_id, token)
            if not state or state['profile_id'] is None:
                return {'profile': None, 'restricted': bool(state and state['restricted'])}
            profile = owned_profile(cur, account_id, state['profile_id'])
            selected = SelectedProfile(**profile, restricted=state['restricted'],
                                       genre_ids=tuple(genre_ids(cur, profile['id'])))
            return {'profile': asdict(selected), 'restricted': selected.restricted}
