# Smart Building Backend

[![Backend CI](https://github.com/atefekalamati/bamboPlatform/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/atefekalamati/bamboPlatform/actions/workflows/backend-ci.yml)

This backend provides the initial foundation for a smart building management platform built with Python, FastAPI, SQLAlchemy, and SQLite.

## Features
- Building / structure domain model
- Equipment and sensor models
- Pydantic schemas for request and response validation
- FastAPI application with health endpoint
- SQLAlchemy database session management

## Project Structure
- app/models: ORM models
- app/schemas: Pydantic schemas
- app/database.py: database engine and session setup
- app/main.py: FastAPI entry point
- tests: regression tests for models and API

## Run locally
```bash
cd smart-building-backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing
```bash
pytest -q
```

## Notes
The project documentation file BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md remains the product/requirements reference for the platform.

## Contributors

- [Your Name](https://github.com/your-username) — Backend and project management
- [Frontend Developer](https://github.com/frontend-username) — Frontend development
