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
├── ml/               # Graph Neural Network (HeteroGraphSAGE) engine
│   ├── seed_gnn_data.py # Diverse Indonesian scam & legit dataset generator
│   ├── export_graph.py  # PyG HeteroData graph exporter
│   ├── train_sage.py    # HeteroGraphSAGE trainer
│   ├── gnn_service.py   # Production inference service
│   └── audit_db.py      # Database training readiness auditor
└── tests/
```

---

## GNN Anti-Scam Intelligence Pipeline

CekInvest utilizes a **HeteroGraphSAGE** Graph Neural Network to detect fraud syndicates and multi-entity scam operations (connected bank accounts, phone numbers, and domains).

### 1. Collect & Seed GNN Training Dataset
```bash
# Seeds 110+ balanced Indonesian scam & legitimate reports, plus community databases
python -m ml.seed_gnn_data
# Or run complete intelligence seed:
python -m app.seed
```

### 2. Audit Database Readiness
```bash
python -m ml.audit_db
```

### 3. Export Graph Dataset
```bash
python -m ml.export_graph
```
Generates `ml/models/gnn_dataset.pt`, `ml/models/tfidf_vectorizer.pkl`, and `ml/models/gnn_metadata.json`.

### 4. Train HeteroGraphSAGE Model
```bash
python -m ml.train_sage
```
Trains the model across Train/Val/Test splits and saves the weights to `ml/models/gnn_model.pt`.

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

---

## 🚀 Render Free Plan Deployment (512 MB RAM Optimized)

CekInvest backend dirancang dengan arsitektur **Graceful Degradation & Circuit Breaker** agar dapat berjalan dengan stabil 100% pada **Render Free Plan (512 MB RAM limit)** tanpa risiko OOM (Out Of Memory) crash:

### 1. Konfigurasi di Render Dashboard:
- **Environment**: `Docker`
- **Docker Command / Entrypoint**: Ditangani otomatis oleh `backend/entrypoint.sh` (mendukung dynamic `$PORT`).
- **Plan**: `Free`
- **Health Check Path**: `/api/v1/health`

### 2. Environment Variables Wajib di Render:
| Variable | Value Rekomendasi | Keterangan |
|---|---|---|
| `ENABLE_GNN` | `false` | **Wajib `false` di Render Free** agar RAM di bawah 150 MB (tanpa PyTorch). |
| `DATABASE_URL` | `postgresql://...` | Connection string PostgreSQL (Supabase / Neon). |
| `GEMINI_API_KEY` | `AIzaSy...` | API Key Google Gemini (SENTRA Engine). |
| `FRONTEND_URL` | `https://cekinvest.vercel.app` | URL Frontend production. |
| `CORS_ORIGINS` | `["*"]` atau domain frontend | Pengaturan CORS. |

### 3. Alur Sinkronisasi GNN (Local to Production Sync):
1. Pengguna melaporkan penipuan di web produksi Render $\rightarrow$ tersimpan ke PostgreSQL.
2. Dari komputer lokal (laptop/PC yang memiliki RAM leluasa), jalankan sinkronisasi graf dan klaster ke database produksi:
   ```bash
   python -m ml.export_graph
   ```
3. Begitu proses lokal selesai, halaman **Scam Radar** di website produksi langsung membaca klaster penipuan terbaru dari tabel `scam_clusters` secara instan tanpa perlu merestart server Render!
