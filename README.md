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
│   │   ├── payment_method_schema.py
│   │   └── catalog_schema.py    # Catalog & media detail response schemas
│   ├── routers/
│   │   ├── accounts.py          # Account API endpoints
│   │   ├── payment_methods.py   # Payment method API endpoints
│   │   └── catalog.py           # Catalog, search & media detail API endpoints
│   └── services/
│       ├── account_services.py  # Business logic & SQL queries
│       ├── payment_method_services.py
│       └── catalog_services.py  # Catalog queries, filters & search
├── frontend/                    # Landing page & UI files (index.html)
│   ├── pages/                   # register.html, payment.html, catalog.html, media.html
│   ├── scripts/                 # landing.js, register.js, payment.js, catalog-api.js, catalog.js, media.js
│   └── styles/                  # global.css, landing.css, auth.css, payment.css, catalog.css
├── tests/
│    ├── test_account.py                  # Pytest integration tests (accounts)
│    ├── test_payment_method.py           # Pytest integration tests (payment methods API)
│    ├── test_payment_method_models.py    # Unit tests (no database needed)
│    ├── test_catalog.py                  # RF10–RF12 PostgreSQL integration tests
│    └── test_catalog_api.py              # HTTP validation, access control & errors
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
   pip install -r requirements.txt
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

## Subscription lifecycle (RF05–RF06)

For an existing database, apply the subscription migration after migration 002:

```bash
psql -h localhost -U postgres -d quaseflix -v ON_ERROR_STOP=1 \
  -f backend/database/migrations/003_subscription.sql
```

Fresh databases include these tables in `schema.sql`. The migration does not
charge existing accounts. Starting the worker processes any elapsed billing
periods for non-canceled accounts; use a separate local test database for demos.

Keep the API and frontend running as described above. In a third terminal,
activate the same virtual environment and start the billing worker:

```bash
python -m backend.billing_worker
```

It checks once per minute. `python -m backend.billing_worker --once` processes
currently due subscriptions and writes pending simulated billing emails once.
No clock or trial-duration setting needs to be changed. The automated integration
tests create their own dated test accounts to cover expiry.

Open `http://localhost:5500/pages/subscription.html`, also linked from login and
profiles. This screen supports management login even when normal access is
blocked, displays invoices and debt, lets the owner choose an existing payment
method or add a simulated boleto, confirms simulated settlement, cancels the
subscription, and restores canceled accounts. Cancellation clears the browser
session and normal login is refused while the account is canceled.

Billing rules used in this demonstration:

- The trial lasts exactly 30 days from account creation. After that, the account
  becomes ACTIVE and the selected plan is billed each calendar month. Month-end
  dates are clamped to the last valid day of the following month.
- The newest registered payment method is used for automatic billing. Valid
  cards simulate successful charges; expired or missing cards leave unpaid debt.
  Boleto invoices remain unpaid until explicitly settled in the management UI,
  with a three-day payment window. No real money is collected.
- ACTIVE accounts with overdue unpaid invoices cannot use normal login or
  protected content, but management login remains available. Payment restores
  eligibility; it does not reactivate an explicitly canceled account.
- Cancellation requires all outstanding invoices to be settled, including
  pending boletos. It then stops billing immediately. Canceling during an
  unexpired trial incurs no invoice.
- Restoration preserves the original trial end and any remaining paid period.
  Otherwise it starts a new billing period immediately. It never charges for
  time spent canceled or awards a fresh trial.
- Billing catches up elapsed periods while the worker was stopped for an active
  account. Account locks and unique invoice periods prevent duplicate invoices.
  Plan price changes apply to future invoices; issued amounts are retained.
- Simulated billing emails use a durable database outbox and deterministic local
  files named `billing-<id>.json` in `QUASEFLIX_OUTBOX` (default
  `/tmp/quaseflix-outbox`). Failed file delivery is retried by the worker.

New API routes are grouped under `/api/subscription` in Swagger. They derive the
account from a signed token, not a client-supplied account ID. The management
login verifies the same password without requiring an active subscription.

Integration tests in `tests/test_subscription_integration.py` require
`QUASEFLIX_TEST_DATABASE_URL` pointing to an initialized disposable database.
They create and remove their own accounts and plans. All other existing database
tests still use the connection configured in `backend/database/connection.py`.

## Profiles and preferences (RF07–RF09)

For an existing database, apply migration 004 after migrations 002 and 003:

```bash
psql -h localhost -U postgres -d quaseflix -v ON_ERROR_STOP=1 \
  -f backend/database/migrations/004_profiles.sql
```

The fresh schema includes this migration. It adds a **Principal** profile to
accounts with no profiles and installs a trigger so new accounts receive their
first profile in the account creation transaction. Existing profiles are kept.
The migration stops with an explicit error if legacy data has orphaned profiles,
empty names, duplicate names ignoring case and surrounding spaces, or more than
four profiles for an account. Resolve those records before retrying.

After login, `frontend/pages/profiles.html` provides profile selection, creation,
editing, deletion, genre preferences, and the child-profile setting. Accounts
must retain 1–4 profiles. Names are trimmed, limited to 100 characters, and unique
within each account ignoring case. Profile writes lock the account row so
concurrent requests cannot exceed four profiles or delete the last one.
Preferences are optional, isolated per profile, and can be cleared. Genre IDs
must refer to the shared seeded genre list.

Selection is associated with the signed login token in `profile_session`.
Tokens have a unique `jti`, so separate logins can select different profiles.
The browser caches the selection only for display; the server remains the
source of truth. A selected child profile locks that session to child mode.
Clearing browser profile data or deleting the selected profile in another
session cannot remove the lock. Switching to an unrestricted profile requires
the owner's account password. Profile creation, edits, and deletion from child
mode also require that password. Turning off a profile's child setting always
requires owner confirmation, even from an adult session. Confirmation passwords
are verified per operation and are never stored in profile/session records.

API routes (all require a current, eligible account):

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/genres` | Available genres |
| GET | `/api/profiles` | Current account's profiles and preferences |
| POST | `/api/profiles` | Create `{name, is_kids, genre_ids, password?}` |
| PUT | `/api/profiles/{id}` | Replace name, child setting and preferences |
| DELETE | `/api/profiles/{id}` | Delete with JSON `{}` or `{password}` |
| POST | `/api/profiles/{id}/select` | Select with JSON `{}` or `{password}` |
| GET | `/api/profiles/current` | Authoritative selected profile and restriction state |

Requests never accept an account ID for profile ownership. Foreign profile IDs
return 404. Canceled/overdue accounts must use subscription management instead.

**Catalog integration (RF10–RF12).** Select a profile and choose "Explorar catálogo"
to browse, filter, search and view media details. Catalog endpoints require the
server-side profile selection. Lists and suggestions apply the child-content
restriction in SQL before pagination and rank preferred genres first; details
use the shared content policy. Playback remains outside this module.
`media.age_rating` accepts 0 (Livre), 10, 12, 14, 16, 18 or NULL.
Child mode allows only explicitly classified Livre titles; unknown ratings are
excluded. Content is filtered before ranking by preferred genres. If no eligible
title matches the preferences, the complete eligible collection remains visible.
No frontend filtering or client-provided profile ID may replace these checks.

Profile integration tests require `QUASEFLIX_TEST_DATABASE_URL` pointing to an
initialized disposable database, as with the subscription integration tests.

Existing databases also need `backend/database/migrations/002_catalog.sql` for
catalog languages and popularity. It is separate from `002_registration.sql`;
apply both, along with the subscription and profile migrations. New databases
already include all modules in `schema.sql`. Demo data in
`backend/database/seeds/catalog_demo.sql` is unclassified and consequently hidden
from child profiles until a rating is explicitly assigned.
