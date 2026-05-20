# CekInvest Backend

> AI Scam Intelligence Platform — powered by **SENTRA** (Gemini)

---

## Overview

CekInvest backend is a production-grade **Python/FastAPI** REST API that powers an AI-driven financial scam detection engine. Users can paste chat messages, upload screenshots, or submit URLs — and SENTRA will analyze them for scam patterns, psychological manipulation, and financial fraud indicators.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| AI Engine | SENTRA (Google Gemini) |
| Database | **Prisma Postgres** |
| ORM | **Prisma Client Python** (auto-generated, type-safe) |
| Validation | Pydantic v2 |
| OCR | pytesseract (Tesseract) |
| Package Manager | uv |

---

## Quick Start

### 1. Install Dependencies

```bash
pip install uv
uv sync --dev
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL and GEMINI_API_KEY
```

**Prisma Postgres (managed):**
```
DATABASE_URL="prisma+postgres://accelerate.prisma-data.net/?api_key=YOUR_API_KEY"
```

**Standard PostgreSQL:**
```
DATABASE_URL="postgresql://user:password@localhost:5432/cek_invest"
```

### 3. Generate Prisma Client

```bash
# Must add venv Scripts to PATH so the generator is found
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"   # Windows PowerShell
# source .venv/bin/activate                   # Linux/macOS

python -m prisma generate
```

### 4. Run Database Migrations

```bash
python -m prisma migrate dev --name init
```

### 5. Seed SENTRA's Intelligence Database

```bash
python -m app.seed
```

### 6. Start the Development Server

```bash
uvicorn app.main:app --reload
```

API: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | ❌ | Health check |
| `POST` | `/api/v1/analysis/chat` | ❌ | Analyze chat/text |
| `POST` | `/api/v1/analysis/screenshot` | ❌ | Analyze screenshot |
| `POST` | `/api/v1/analysis/url` | ❌ | Analyze URL |
| `GET` | `/api/v1/analysis/{id}` | ❌ | Get analysis result |
| `POST` | `/api/v1/reports` | ❌ | Submit report |
| `GET` | `/api/v1/reports` | ❌ | List reports |
| `GET` | `/api/v1/intelligence/patterns` | ❌ | Scam patterns |
| `GET` | `/api/v1/intelligence/stats` | ❌ | Platform stats |

---

## SENTRA AI Pipeline

```
Input (chat / screenshot / URL)
  → OCR (if screenshot, pytesseract)
  → SENTRA (Gemini) — structured JSON analysis
  → Risk Scorer (AI score + pattern DB boost)
  → Persist to PostgreSQL
  → Return explainable report
```

---

## Running Tests

```bash
# Install test dependencies
uv sync --dev

# Run all tests
pytest tests/ -v
```

---

## Project Structure

```
backend/
├── prisma/           # Prisma schema and migrations
├── app/
│   ├── main.py       # FastAPI app factory
│   ├── config.py     # Settings (pydantic-settings)
│   ├── database.py   # Prisma client singleton
│   ├── dependencies.py
│   ├── schemas/      # Pydantic v2 schemas
│   ├── routers/      # FastAPI route handlers
│   ├── services/     # Business logic
│   │   ├── sentra_service.py  ← SENTRA AI core
│   │   ├── analysis_service.py
│   │   ├── ocr_service.py
│   │   └── risk_scorer.py
│   ├── utils/
│   └── seed.py       # Intelligence DB seed
└── tests/
```

---

## OCR Setup (for Screenshot Analysis)

Screenshot analysis requires Tesseract OCR to be installed on your system:

**Windows:**
```
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
Install with Indonesian language pack (ind)
```

**Linux/macOS:**
```bash
# Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-ind

# macOS
brew install tesseract
```
