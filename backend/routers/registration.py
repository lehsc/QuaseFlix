"""Local demonstration registration. No real email or payment is sent."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import date
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.database.connection import get_db_connection
from backend.security import hash_password
from backend.models.credit_card import CreditCard
from backend.models.boleto import Boleto

router = APIRouter(prefix="/api/registration", tags=["Registration"])
OUTBOX = Path(os.environ.get("QUASEFLIX_OUTBOX", "/tmp/quaseflix-outbox"))

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def message(email, body):
    OUTBOX.mkdir(mode=0o700, parents=True, exist_ok=True)
    (OUTBOX / (secrets.token_hex(16) + ".json")).write_text(json.dumps({"to": email, "body": body}))

class Start(BaseModel):
    email: str

class Verify(BaseModel):
    token: str
    code: str

class Complete(BaseModel):
    token: str
    full_name: str
    password: str = Field(min_length=10, max_length=128)
    cpf: str
    birth_date: date
    phone: str | None = None
    address: str
    plan_id: int = Field(gt=0)
    payment: dict

def validate_details(data):
    if len(data.full_name.strip().split()) < 2:
        raise ValueError("Enter your full name.")
    cpf = ''.join(c for c in data.cpf if c.isdigit())
    if len(cpf) != 11 or len(set(cpf)) == 1 or not cpf.isascii():
        raise ValueError("Invalid CPF.")
    for length in (9, 10):
        check = (sum(int(cpf[i]) * (length + 1 - i) for i in range(length)) * 10) % 11
        if int(cpf[length]) != (0 if check == 10 else check):
            raise ValueError("Invalid CPF.")
    if data.birth_date >= date.today() or len(data.address.strip()) < 5:
        raise ValueError("Invalid birth date or address.")
    if not any(c.isalpha() for c in data.password) or not any(c.isdigit() for c in data.password):
        raise ValueError("Password must contain letters and numbers.")
    return cpf

@router.post("/start")
def start(data: Start):
    import re
    email = data.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 255:
        raise HTTPException(422, "Invalid email.")
    token, code = secrets.token_urlsafe(32), str(secrets.randbelow(1000000)).zfill(6)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM public.account WHERE lower(email)=%s", (email,))
            if cur.fetchone():
                raise HTTPException(409, "Email already registered.")
            cur.execute("INSERT INTO public.registration_session(token_hash,email,code_hash,expires_at) VALUES (%s,%s,%s,LOCALTIMESTAMP + interval '30 minutes')", (digest(token),email,digest(token+code)))
    message(email, "Verification code: " + code)
    return {"token": token, "delivery": "simulated", "message": "Read the code in the local development outbox."}

@router.post("/verify")
def verify(data: Verify):
    valid = False
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code_hash FROM public.registration_session WHERE token_hash=%s AND expires_at>LOCALTIMESTAMP AND attempts<5 FOR UPDATE", (digest(data.token),))
            row = cur.fetchone()
            if row:
                valid = hmac.compare_digest(row[0], digest(data.token+data.code))
                cur.execute("UPDATE public.registration_session SET attempts=attempts+1,verified=%s WHERE token_hash=%s", (valid,digest(data.token)))
    if not valid:
        raise HTTPException(400, "Invalid or expired code; restart after five failed attempts.")
    return {"verified": True}

@router.post("/complete", status_code=201)
def complete(data: Complete):
    try:
        cpf = validate_details(data)
        if data.payment.get("type") == "credit_card":
            fields = {k:v for k,v in data.payment.items() if k != "type"}
            method = CreditCard(account_id=1, **fields)
        elif data.payment == {"type": "boleto"}:
            method = Boleto.issue(1)
        else:
            raise ValueError("Invalid payment method.")
    except (ValueError, TypeError) as error:
        raise HTTPException(422, str(error))
    from psycopg.errors import UniqueViolation
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email,google_subject FROM public.registration_session WHERE token_hash=%s AND verified AND expires_at>LOCALTIMESTAMP FOR UPDATE", (digest(data.token),))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(401, "Verify your email or restart registration.")
                email = row[0]
                cur.execute("SELECT 1 FROM public.plan WHERE id=%s", (data.plan_id,))
                if not cur.fetchone():
                    raise HTTPException(422, "Invalid plan.")
                cur.execute("INSERT INTO public.account(email,password_hash,cpf,birth_date,phone,address,plan_id,full_name,google_subject) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (email,hash_password(data.password),cpf,data.birth_date,data.phone,data.address.strip(),data.plan_id,data.full_name.strip(),row[1]))
                account_id = cur.fetchone()[0]
                cur.execute("INSERT INTO public.payment_method(account_id,type) VALUES (%s,%s) RETURNING id", (account_id,method.payment_type.value))
                payment_id = cur.fetchone()[0]
                if isinstance(method, CreditCard):
                    cur.execute("INSERT INTO public.credit_card_details VALUES (%s,%s,%s,%s,%s)", (payment_id,*method.details().values()))
                else:
                    cur.execute("INSERT INTO public.boleto_details VALUES (%s,%s,%s)", (payment_id,method.barcode,method.due_date))
                cur.execute("DELETE FROM public.registration_session WHERE email=%s", (email,))
    except UniqueViolation:
        raise HTTPException(409, "Email or CPF already registered.")
    try:
        message(email, "Registration complete. Your 30-day trial has started. Payments are simulated.")
    except OSError:
        import logging
        logging.getLogger(__name__).exception("Unable to write confirmation to development outbox")
    return {"id":account_id,"status":"trial","payment_mode":"simulated"}

class GoogleCredential(BaseModel):
    credential: str

@router.get("/config")
def config():
    return {"google_client_id": os.environ.get("GOOGLE_CLIENT_ID"), "mode": "simulated"}

@router.post("/google")
def google_registration(data: GoogleCredential):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(503, "Google sign-in is not configured.")
    from google.oauth2 import id_token
    from google.auth.transport import requests
    try:
        identity = id_token.verify_oauth2_token(data.credential, requests.Request(), client_id)
        if not identity.get("email_verified"):
            raise ValueError("Unverified Google email")
        email = identity["email"].lower()
    except (ValueError, KeyError):
        raise HTTPException(401, "Invalid Google identity.")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM public.account WHERE google_subject=%s", (identity["sub"],))
            existing = cur.fetchone()
            if existing:
                from backend.services.auth_services import get_account_for_access
                from backend.security import create_access_token
                from backend.exceptions import AccountCanceledError, SubscriptionExpiredError
                try:
                    account = get_account_for_access(existing[0])
                except (AccountCanceledError, SubscriptionExpiredError):
                    raise HTTPException(403, "Account is not currently eligible for access.")
                return {"access_token": create_access_token(account.id), "account": account.to_dict()}
            cur.execute("SELECT 1 FROM public.account WHERE lower(email)=%s", (email,))
            if cur.fetchone():
                raise HTTPException(409, "An account already exists. Sign in with your password; automatic account linking is disabled.")
            token = secrets.token_urlsafe(32)
            cur.execute("INSERT INTO public.registration_session(token_hash,email,code_hash,expires_at,verified,google_subject) VALUES (%s,%s,%s,LOCALTIMESTAMP + interval '30 minutes',true,%s)", (digest(token),email,digest(secrets.token_urlsafe(32)),identity["sub"]))
    return {"token":token,"verified":True}
