---
title: IIIF Studio
emoji: 📜
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# IIIF Studio

A generic platform for generating AI-augmented scholarly editions from digitized heritage documents — medieval manuscripts, incunabula, cartularies, archives, charters, papyri. Any document type, any era, any language.

IIIF Studio ingests images from any [IIIF](https://iiif.io/)-compliant server, analyzes them with multimodal AI (Google Gemini, Mistral), and produces structured scholarly data: diplomatic OCR, layout detection, translations, commentaries, and iconographic analysis — all exportable as ALTO XML, METS, and IIIF Presentation 3.0 manifests.

**Images are never stored locally.** The platform streams them from origin servers using the IIIF Image API, storing only the AI-generated metadata (~5 KB per page instead of ~50 MB).

---

## Features

- **IIIF-native architecture** — images streamed from origin servers (Gallica, BnF, Bodleian, etc.) with tiled deep zoom via OpenSeadragon
- **Multi-provider AI** — Google AI Studio, Vertex AI, Mistral AI. Model selected per corpus, auto-detected from environment
- **Profile-driven analysis** — 4 built-in corpus profiles (medieval illuminated, medieval textual, early modern print, modern handwritten), each with tailored prompts and active layers
- **Structured output** — layout regions with bounding boxes, diplomatic OCR, translations (FR/EN), scholarly and public commentary, iconographic analysis, uncertainty tracking
- **Standards-compliant export** — IIIF Presentation 3.0 manifests (with Image Service for tiled zoom), ALTO XML, METS XML, ZIP bundles
- **Human-in-the-loop** — editorial correction interface with versioned history and rollback
- **Full-text search** — accent-insensitive search across OCR text, translations, and iconographic tags

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          IIIF IMAGE SERVERS                                     │
│                  Gallica · BnF · Bodleian · Europeana · ...                     │
│                  (origin — images are never copied)                             │
└──────────┬────────────────────┬─────────────────────────────┬───────────────────┘
           │                    │                             │
           │ info.json          │ /full/!1500,1500/           │ /full/max/
           │ + tiles            │ 0/default.jpg               │ 0/default.jpg
           │                    │ (1500px for AI)             │
           │                    │                             │
┌──────────▼──────────┐ ┌──────▼───────────┐ ┌──────────────▼──────────────────┐
│                     │ │                  │ │                                 │
│   FRONTEND (SPA)    │ │  BACKEND (API)   │ │    EXPORT GENERATORS            │
│   React + Vite      │ │  FastAPI         │ │                                 │
│                     │ │                  │ │  IIIF Manifest 3.0              │
│ ┌─────────────────┐ │ │ ┌──────────────┐ │ │  (with Image Service refs)      │
│ │  OpenSeadragon   │ │ │ │  Ingestion   │ │ │                                 │
│ │  IIIF tiled zoom │ │ │ │              │ │ │  METS XML                       │
│ │  (info.json →    │ │ │ │ manifest URL │ │ │  (IIIF URLs, not file paths)    │
│ │   deep zoom)     │ │ │ │ → detect svc │ │ │                                 │
│ └────────┬─────────┘ │ │ │ → store meta │ │ │  ALTO XML                       │
│          │           │ │ └──────┬───────┘ │ │  (text geometry per page)        │
│ ┌────────▼─────────┐ │ │       │         │ │                                 │
│ │ Region overlays  │ │ │ ┌─────▼────────┐│ │  ZIP bundle                     │
│ │ (bbox from       │ │ │ │  AI Pipeline ││ │  (manifest + METS + ALTO)       │
│ │  master.json,    │ │ │ │             ││ └─────────────────────────────────┘
│ │  scaled to       │ │ │ │ fetch 1500px││
│ │  canvas coords)  │ │ │ │ in memory   ││        ┌──────────────────────┐
│ └──────────────────┘ │ │ │      │      ││        │                      │
│                     │ │ │      ▼      ││        │   AI PROVIDERS        │
│ ┌──────────────────┐ │ │ │ send bytes  │├───────►│                      │
│ │  Pages           │ │ │ │ to AI       ││        │ Google Gemini        │
│ │  Home · Reader   │ │ │ │      │      ││◄───────│ Vertex AI            │
│ │  Editor · Admin  │ │ │ │      ▼      ││  JSON  │ Mistral AI           │
│ └────────┬─────────┘ │ │ │ discard img ││        │                      │
│          │           │ │ │ keep JSON   ││        │ (auto-detected from  │
│          │ REST API  │ │ │ scale bbox  ││        │  environment vars)   │
│          │ /api/v1/* │ │ └─────┬───────┘│        └──────────────────────┘
└──────────┼───────────┘ │       │         │
           │             │ ┌─────▼────────┐│
           │             │ │  Response    ││
           │             │ │  Parser     ││
           └─────────────┤ │             ││
                         │ │ raw JSON    ││
                         │ │ → layout    ││
                         │ │ → OCR       ││
                         │ │ → regions   ││
                         │ └─────┬───────┘│
                         │       │         │
                         │ ┌─────▼────────┐│
                         │ │  Master      ││
                         │ │  Writer      ││
                         │ │             ││
                         │ │ ai_raw.json ││    ┌───────────────────────────────┐
                         │ │ master.json ││    │                               │
                         │ └─────┬───────┘│    │   LOCAL STORAGE               │
                         │       │         │    │                               │
                         └───────┼─────────┘    │   SQLite (corpus, pages,     │
                                 │              │   manuscripts, jobs, models)  │
                                 └──────────────►                               │
                                                │   data/corpora/{slug}/pages/  │
                                                │     {folio}/master.json       │
                                                │     {folio}/ai_raw.json       │
                                                │     {folio}/alto.xml          │
                                                │                               │
                                                │   ~5 KB per page (JSON only)  │
                                                │   NO image binaries           │
                                                └───────────────────────────────┘

PIPELINE FLOW (per page):

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ 1.INGEST │───►│ 2.DETECT │───►│ 3.FETCH  │───►│ 4.AI     │───►│ 5.PARSE  │
  │          │    │          │    │          │    │          │    │          │
  │ manifest │    │ IIIF svc │    │ 1500px   │    │ send     │    │ layout   │
  │ URL      │    │ URL +    │    │ JPEG in  │    │ image +  │    │ regions  │
  │          │    │ canvas   │    │ memory   │    │ prompt   │    │ OCR      │
  │          │    │ dims     │    │ (discard │    │ to       │    │ bbox     │
  │          │    │          │    │  after)  │    │ provider │    │          │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                                       │
  ┌──────────┐    ┌──────────┐    ┌──────────┐                   ┌────▼─────┐
  │ 8.EXPORT │◄───│ 7.REVIEW │◄───│ 6.WRITE  │◄──────────────────│ 5b.SCALE │
  │          │    │          │    │          │                   │          │
  │ IIIF 3.0 │    │ human    │    │ ai_raw + │                   │ bbox     │
  │ ALTO XML │    │ correct  │    │ master   │                   │ deriv →  │
  │ METS XML │    │ validate │    │ .json    │                   │ canvas   │
  │ ZIP      │    │ version  │    │ + ALTO   │                   │ coords   │
  └──────────┘    └──────────┘    └──────────┘                   └──────────┘
```

### Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | SQLite via SQLAlchemy 2.0 async + aiosqlite |
| Validation | Pydantic v2 |
| AI providers | Google Gemini (google-genai SDK), Mistral AI |
| Image viewer | OpenSeadragon (IIIF tiled zoom) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| Exports | lxml (ALTO/METS XML), IIIF Presentation 3.0 |
| Deployment | Docker (HuggingFace Spaces) |

---

## Quick start

### Docker (recommended)

```bash
git clone https://github.com/maribakulj/IIIF-Studio.git && cd IIIF-Studio

# Configure at least one AI provider key
cp .env.example .env
# Edit .env and add your API key(s)

# Build and run
docker compose -f infra/docker-compose.yml up --build

# Open http://localhost:7860
```

### Local development

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 7860

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The API is available at `http://localhost:7860/api/v1/`. Interactive Swagger docs at `http://localhost:7860/docs`.

---

## Usage workflow

1. **Create a corpus** — select a profile matching your document type
2. **Ingest pages** — provide a IIIF manifest URL, direct image URLs, or upload files
3. **Select an AI model** — choose a provider and model from the detected options
4. **Run the pipeline** — AI analyzes each page: layout detection, OCR, translation, commentary
5. **Review and correct** — use the Editor to validate, correct OCR, adjust regions
6. **Export** — download IIIF manifest, ALTO XML, METS XML, or a ZIP bundle

---

## Corpus profiles

Profiles control which analysis layers are active, which prompt templates are used, and what uncertainty thresholds apply.

| Profile | Script | Languages | Key layers |
|---------|--------|-----------|------------|
| `medieval-illuminated` | Caroline | Latin, French | OCR, translation, iconography, commentary, material notes |
| `medieval-textual` | Gothic | Latin, French | OCR, translation, scholarly commentary |
| `early-modern-print` | Print | French, Latin | OCR, summary |
| `modern-handwritten` | Cursive | French | OCR, summary |

Custom profiles can be added as JSON files in the `profiles/` directory with matching prompt templates in `prompts/`.

---

## AI providers

The backend auto-detects available providers from environment variables. No global selector — the model is chosen per corpus from the admin interface.

| Provider | Environment variable | Notes |
|----------|---------------------|-------|
| Google AI Studio | `GOOGLE_AI_STUDIO_API_KEY` | Free tier, good for development |
| Vertex AI (service account) | `VERTEX_SERVICE_ACCOUNT_JSON` | Institutional deployments |
| Mistral AI | `MISTRAL_API_KEY` | Alternative provider |

At least **one** key is required for the pipeline to function. Keys must **never** appear in code, commits, or Docker images.

---

## API reference

All endpoints are prefixed with `/api/v1/`. Full OpenAPI docs available at `/docs`.

### Corpus management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/corpora` | List all corpora |
| `POST` | `/corpora` | Create a corpus (slug + title + profile) |
| `GET` | `/corpora/{id}` | Get a corpus |
| `DELETE` | `/corpora/{id}` | Delete a corpus (cascades) |
| `GET` | `/corpora/{id}/manuscripts` | List manuscripts in a corpus |

### Ingestion
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/corpora/{id}/ingest/iiif-manifest` | Ingest from a IIIF manifest URL |
| `POST` | `/corpora/{id}/ingest/iiif-images` | Ingest from direct image URLs |
| `POST` | `/corpora/{id}/ingest/files` | Upload image files |

### AI pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/providers` | List detected AI providers |
| `GET` | `/providers/{type}/models` | List models for a provider |
| `PUT` | `/corpora/{id}/model` | Set AI model for a corpus |
| `POST` | `/corpora/{id}/run` | Run pipeline on all pages |
| `POST` | `/pages/{id}/run` | Run pipeline on a single page |
| `GET` | `/jobs/{id}` | Check job status |
| `POST` | `/jobs/{id}/retry` | Retry a failed job |

### Pages and content
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/pages/{id}` | Page metadata |
| `GET` | `/pages/{id}/master-json` | Full page master (canonical JSON) |
| `GET` | `/pages/{id}/layers` | List annotation layers |
| `POST` | `/pages/{id}/corrections` | Apply editorial corrections |
| `GET` | `/pages/{id}/history` | Version history |
| `GET` | `/search?q=` | Full-text search across all pages |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/manuscripts/{id}/iiif-manifest` | IIIF Presentation 3.0 manifest |
| `GET` | `/manuscripts/{id}/mets` | METS XML |
| `GET` | `/pages/{id}/alto` | ALTO XML |
| `GET` | `/manuscripts/{id}/export.zip` | ZIP bundle (manifest + METS + ALTO) |

---

## Data model

Each analyzed page produces a `master.json` — the canonical source of truth for all exports.

```
PageMaster
├── image          → IIIF service URL, canvas dimensions, provenance
├── layout         → regions with bounding boxes [x, y, w, h] in absolute pixels
├── ocr            → diplomatic text, confidence, uncertain segments
├── translation    → French, English
├── summary        → short + detailed
├── commentary     → public, scholarly, sourced claims with certainty levels
├── extensions     → profile-specific data (iconography, materiality, etc.)
├── processing     → provider, model, prompt version, timestamp
└── editorial      → status (machine_draft → validated → published), version
```

Bounding boxes follow the convention `[x, y, width, height]` in absolute pixels of the original image. Coordinates are automatically scaled from AI analysis space to full canvas dimensions.

---

## IIIF-native image handling

IIIF Studio operates in two modes:

### IIIF-native mode (default for manifest/URL ingestion)
- Images are **never downloaded or stored** locally
- At ingestion: IIIF Image Service URL and canvas dimensions are extracted from the manifest
- At analysis: a 1500px derivative is fetched in memory via the IIIF Image API (`{service}/full/!1500,1500/0/default.jpg`), sent to the AI, then discarded
- In the viewer: OpenSeadragon loads `info.json` from the IIIF server for native tiled deep zoom
- Storage per page: **~5 KB** (JSON metadata only)

### File upload mode (for non-IIIF sources)
- Uploaded images are stored locally in `data/corpora/{slug}/`
- Derivatives (1500px) and thumbnails (256px) are created on disk
- Storage per page: **~50 MB** (images + JSON)

---

## Project structure

```
IIIF-Studio/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings from env vars
│   │   ├── api/v1/              # REST endpoints
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic v2 schemas (canonical)
│   │   └── services/
│   │       ├── ai/              # Provider factory, analyzer, prompt loader
│   │       ├── ingest/          # IIIF fetcher, service detection
│   │       ├── image/           # Normalizer (in-memory + legacy disk)
│   │       └── export/          # ALTO, METS, IIIF manifest generators
│   ├── tests/                   # 585 tests (pytest + pytest-asyncio)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # React Router (/, /admin, /reader, /editor)
│   │   ├── lib/api.ts           # Typed API client
│   │   ├── pages/               # Home, Reader, Editor, Admin
│   │   └── components/          # Viewer (OpenSeadragon), retro UI system
│   └── package.json
├── profiles/                    # 4 corpus profile JSON files
├── prompts/                     # 9 prompt templates organized by profile
├── Dockerfile                   # Multi-stage build (Node + Python)
├── infra/docker-compose.yml     # Local development
└── .env.example                 # Environment variable template
```

---

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v --cov=app
```

Expected result: **585 passed, 3 skipped**.

All AI calls are mocked in tests — no API keys required to run the test suite.

---

## Deployment

### HuggingFace Spaces

This repository is configured for [HuggingFace Spaces](https://huggingface.co/spaces) with Docker SDK on port 7860. AI keys are stored as Space secrets (Settings → Repository secrets).

The CI pipeline (`.github/workflows/`) runs tests on every push and auto-deploys to HuggingFace Spaces on merge to `main`.

### Self-hosted

```bash
docker build -t iiif-studio .
docker run -p 7860:7860 \
  -e GOOGLE_AI_STUDIO_API_KEY=your_key \
  -v ./data:/app/data \
  iiif-studio
```

---

## License

[Apache License 2.0](LICENSE)
