# QuaseFlix

A full-stack streaming platform project featuring a FastAPI + PostgreSQL backend and a responsive frontend landing/authentication experience.

---

## Prerequisites

Before running the project, make sure you have the following installed on your machine:

* **Python 3.10+**
* **PostgreSQL 14+** (running on port `5432`)
* **Git**

---

## Project Structure

```text
QuaseFlix/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint
│   ├── exceptions.py            # Domain exceptions (AccountNotFoundError)
│   ├── database/
│   │   ├── connection.py        # PostgreSQL connection context manager
│   │   ├── schema.sql           # Database tables & schema definition
│   │   └── migrations/          # Changes for databases created before a schema update
│   ├── models/
│   │   ├── account.py           # Account domain model
│   │   ├── payment_method.py    # Abstract payment method
│   │   ├── credit_card.py       # Credit card (validates, never stores number/CVC)
│   │   ├── boleto.py            # Boleto (issued by the system)
│   │   └── payment_type.py      # PaymentType enum
│   ├── schemas/
│   │   ├── account_schema.py    # Pydantic request schemas
│   │   └── payment_method_schema.py
│   ├── routers/
│   │   ├── accounts.py          # Account API endpoints
│   │   └── payment_methods.py   # Payment method API endpoints
│   └── services/
│       ├── account_services.py  # Business logic & SQL queries
│       └── payment_method_services.py
├── frontend/                    # Landing page & UI files (index.html)
│   ├── pages/                   # register.html, payment.html
│   ├── scripts/                 # landing.js, register.js, payment.js
│   └── styles/                  # global.css, landing.css, auth.css, payment.css
├── tests/
│   ├── test_account.py                  # Pytest integration tests (accounts)
│   ├── test_payment_method.py           # Pytest integration tests (payment methods API)
│   └── test_payment_method_models.py    # Unit tests (no database needed)
├── pytest.ini                   # Pytest path configuration
└── README.md
```

---

## 1. Database Setup (PostgreSQL)

1. **Create the database and user** (matching `backend/database/connection.py`):

   ```bash
   psql -h localhost -p 5432 -U postgres
   ```

   Inside the `psql` shell, run:

   ```sql
   CREATE DATABASE quaseflix;
   \q
   ```

2. **Run the database schema script** located in `backend/database/schema.sql`:

   ```bash
   psql -h localhost -p 5432 -U postgres -d quaseflix -f backend/database/schema.sql
   ```

3. **Insert the default subscription plan** (`plan_id = 1`):

   Connect to the database (`psql -h localhost -p 5432 -U postgres -d quaseflix`) and run:

   ```sql
   INSERT INTO public.plan (id, name, price, description)
   VALUES (1, 'Padrão', 25.90, 'Acesso ilimitado ao catálogo  para assistir em 1 tela por vez.')
   ON CONFLICT (id) DO NOTHING;
   ```

4. **Existing databases only:** if you created the database before the payment method feature, apply the migration (new databases already get it from `schema.sql`). It removes the `cvc` column from `credit_card_details`, because the CVC must not be stored:

   ```bash
   psql -h localhost -p 5432 -U postgres -d quaseflix -f backend/database/migrations/001_credit_card_drop_cvc.sql
   ```

---

## 2. Backend Setup

1. **Clone the repository and navigate to the project root:**
   ```bash
   git clone https://github.com/lehsc/QuaseFlix
   cd QuaseFlix
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required Python packages:**
   ```bash
   pip install fastapi uvicorn "psycopg[binary]" pytest httpx
   ```

---

## 3. Running the Application

### Start the FastAPI Backend
From the **project root directory** (`QuaseFlix/`), run:
```bash
uvicorn backend.main:app --reload
```
* **API Base URL:** `http://127.0.0.1:8000`
* **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

### Open the Frontend
* Open the landing page (`index.html`) directly in your browser or serve it using VS Code's **Live Server** extension (default port `5500`). CORS is pre-configured in `backend/main.py` to accept requests from the frontend.

---

## 4. Payment Methods API

`POST /api/accounts/{account_id}/payment-methods`

Credit card (the full number and the CVC are validated and never stored; only the masked number is saved):

```json
{
  "type": "credit_card",
  "card_number": "4111111111111111",
  "holder_name": "Maria da Silva",
  "cvc": "123",
  "expiration_month": 12,
  "expiration_year": 2030,
  "bank_name": "Banco Exemplo"
}
```

Boleto (issued by the system, no extra fields):

```json
{ "type": "boleto" }
```

| Status | Meaning |
|--------|---------|
| `201`  | Registered. The response has `id`, `type` and the non-sensitive data (`last_four`, or `barcode` and `due_date`). |
| `404`  | The account does not exist. |
| `422`  | Invalid data (bad card number, expired card, unknown `type`, missing field...). |
| `500`  | Unexpected error. |

The registration page (`frontend/pages/payment.html`) reads the account id that `register.js` saves in `sessionStorage`.

---

## 5. Running Automated Tests

To run the `pytest` integration suite from the **project root directory**:

```bash
PYTHONPATH=. pytest
```

The tests in `tests/test_payment_method_models.py` do not use the database, so they can run on their own:

```bash
PYTHONPATH=. pytest tests/test_payment_method_models.py
```

### Debugging Tests in VS Code
To debug tests with breakpoints in VS Code, ensure your `.vscode/launch.json` includes:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Pytest Debug",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/test_account.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```
> **Note:** Since `email` and `cpf` have `UNIQUE` constraints in `public.account`, clear test rows between repeated test runs if your test uses static values.

## Verified registration (RF01–RF03)

Install `pip install -r requirements.txt`. Existing databases must apply
`backend/database/migrations/002_registration.sql` before starting the server.
Resolve any existing email duplicates differing only in case before applying it.
Fresh databases use the updated schema. Seed plan 1 as described above.

Open `frontend/pages/register.html` through a local HTTP server. Email delivery
and payments are simulated: never use real card details. Messages appear as JSON
files in `/tmp/quaseflix-outbox`, configurable with `QUASEFLIX_OUTBOX`.
Codes expire after 30 minutes and allow five attempts. Reloading the same tab
preserves registration progress; expired sessions require restarting. Account,
plan and payment details are committed together only after verified completion.
The existing account creation endpoint now returns 410. Existing plan/payment
mutation endpoints require an authenticated owner.

Passwords require 10–128 characters including letters and numbers; CPF check
digits, full name, address length and birth date are validated server-side.
Phone is optional. Trial starts at final account creation.

For Google registration, configure `GOOGLE_CLIENT_ID` in the server environment
and authorize the frontend origin in Google Cloud. Tokens are verified using
Google's authentication library. Existing email accounts are never automatically
linked; they must use password login. A Google registrant can use Google again or the local password for login. No Google client ID or credentials are included here.

The development outbox is for local demonstrations only. It is not an email
service. Payment details are validation-only, with no provider charge or token.
