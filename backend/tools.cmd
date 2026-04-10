@echo off
if "%1"=="act" .venv\Scripts\activate
if "%1"=="dev" .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000
if "%1"=="test" .venv\Scripts\activate && pytest -v
if "%1"=="lint" .venv\Scripts\activate && ruff check .
if "%1"=="fmt" .venv\Scripts\activate && ruff format .
if "%1"=="pre" .venv\Scripts\activate && ruff format . && ruff check .
if "%1"=="fix" .venv\Scripts\activate && ruff format . && ruff check --fix .
if "%1"=="" echo Usage: tools [act^|dev^|test^|lint^|fmt^|pre^|fix]