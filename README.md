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
│   ├── database/
│   │   ├── connection.py        # PostgreSQL connection context manager
│   │   └── schema.sql           # Database tables & schema definition
│   ├── models/
│   │   └── account.py           # Pydantic models
│   ├── routers/
│   │   └── accounts.py          # Account API endpoints
│   └── services/
│       └── account_services.py  # Business logic & SQL queries
├── frontend/                    # Landing page & UI files (index.html)
├── tests/
│   └── test_account.py          # Pytest integration tests
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

## 4. Running Automated Tests

To run the `pytest` integration suite from the **project root directory**:

```bash
PYTHONPATH=. pytest
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