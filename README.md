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
│   │   └── connection.py        # PostgreSQL connection context manager
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
   ALTER USER postgres WITH PASSWORD 'quaseflix';
   CREATE DATABASE quaseflix;
   \c quaseflix
   ```

2. **Create the required tables** (`plan` and `account`):
   ```sql
   CREATE TABLE IF NOT EXISTS public.plan (
       id SERIAL PRIMARY KEY,
       name VARCHAR(100) NOT NULL
   );

   INSERT INTO public.plan (id, name)
   VALUES (1, 'Básico')
   ON CONFLICT (id) DO NOTHING;

   CREATE TABLE IF NOT EXISTS public.account (
       id SERIAL PRIMARY KEY,
       email VARCHAR(255) UNIQUE NOT NULL,
       password_hash TEXT NOT NULL,
       cpf VARCHAR(14) UNIQUE NOT NULL,
       birth_date DATE NOT NULL,
       phone VARCHAR(20),
       address TEXT,
       plan_id INTEGER REFERENCES public.plan(id) DEFAULT 1
   );
   ```

---

## 2. Backend Setup

1. **Clone the repository and navigate to the project root:**
   ```bash
   git clone <your-repository-url>
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