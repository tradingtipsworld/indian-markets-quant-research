# Windows PowerShell Quick Start & Developer Guide

## 1. Prerequisites
- **Operating System:** Windows 10 or 11 (64-bit)
- **Python:** 3.11+ (Python 3.14 verified)
- **Git for Windows**

## 2. Setup Instructions

Open PowerShell in the project directory:

```powershell
# 1. Clone or navigate to the repository
cd c:\Users\lenovo\Downloads\trading

# 2. (Optional) Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install core dependencies
pip install fastapi uvicorn pydantic-settings sqlalchemy aiosqlite greenlet numpy pandas structlog httpx pytest-asyncio

# 4. Copy environment configuration
Copy-Item .env.example .env

# 5. Run test suite to verify installation
$env:PYTHONPATH="."
python -m pytest tests -v
```

## 3. Running the API Server

Start the local development server with live reload:

```powershell
$env:PYTHONPATH="."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
- **Alternative ReDoc UI:** `http://127.0.0.1:8000/redoc`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`
- **System Readiness Endpoint:** `http://127.0.0.1:8000/api/v1/ready`
