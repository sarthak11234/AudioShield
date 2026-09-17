# 🛡️ AudioShield

**Protect your voice from AI cloning.**

AudioShield is a SaaS platform that applies imperceptible adversarial noise to audio files, disrupting AI voice cloning models (RVC, So-VITS, HuBERT) while preserving audio quality for human listeners.

---

## 🎯 Problem

Generative AI can clone an artist's voice from just 3-10 seconds of audio. Independent artists lack technical resources to protect their intellectual property against these emerging threats.

## 💡 Solution

AudioShield uses **Projected Gradient Descent (PGD)** attacks against the HuBERT feature extractor to inject inaudible perturbations that break voice cloning pipelines.

---

## ✨ Features

- **Drag & Drop Upload** - Simple interface for .wav/.mp3/.flac files (auth required, 50 MB / 10 min limits)
- **Real-time Status** - Poll-based progress tracking (queued → processing → completed)
- **Measured Fidelity** - L∞ perturbation ≤ 0.02, SNR ≈ 17 dB, STOI ≈ 0.92 (LibriSpeech benchmark, see `evaluation/end_to_end_validation.md`)
- **Privacy First** - Files auto-expire after 1 hour (background cleanup)
- **Local-first** - Runs fully on CPU; no commercial APIs (validated on Apple Silicon CPU)

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│   ML Worker     │
│   (Next.js)     │     │   (FastAPI)     │     │   (Celery)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                        ┌──────┴──────┐          ┌──────┴──────┐
                        │  PostgreSQL │          │   PyTorch   │
                        │    Redis    │          │   HuBERT    │
                        └─────────────┘          └─────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Worker | Celery, PyTorch, Torchaudio, HuggingFace Transformers |
| Infra | Docker, PostgreSQL, Redis |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (project `.venv`)
- Node.js 18+
- PostgreSQL 15+ and Redis 7+ — via `docker compose up -d`, **or** natively (e.g. `brew install postgresql@15 redis` + `brew services start postgresql@15 redis`)
- CPU is sufficient (all published validation ran on Apple Silicon CPU); NVIDIA GPU optional

> Port note: `docker-compose.yml` maps host ports **5433** (Postgres) and **6380** (Redis). Native installs typically use defaults **5432/6379**, matching `.env.example`. Set `DATABASE_URL` / `REDIS_URL` accordingly.

### 1. Start Infrastructure
```bash
docker compose up -d
# or: brew services start postgresql@15 redis
```

### 2. Backend
```bash
cd backend
DATABASE_URL="postgresql://admin:audioshield123@localhost:5432/audioshield" \
REDIS_URL="redis://localhost:6379/0" \
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Worker
```bash
cd worker
REDIS_URL="redis://localhost:6379/0" \
../.venv/bin/python -m celery -A celery_app worker --pool=solo --loglevel=info
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

| Service | Local URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

---

## 📡 API Endpoints

All `/api` routes except signup/login require `Authorization: Bearer <JWT>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/auth/signup` | Register (username, email, password) → JWT |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/upload` | Upload audio file → task (202) |
| GET | `/api/status/{id}` | Task status (queued/processing/completed/failed) |
| GET | `/api/task/{id}` | Task detail |
| GET | `/api/tasks` | List own tasks |
| DELETE | `/api/task/{id}` | Delete task + files |
| GET | `/api/download/{id}` | Download protected WAV (auth header required) |

**Swagger Docs:** http://localhost:8000/docs

---

## 📁 Project Structure

```
AudioShield/
├── frontend/          # Next.js application
├── backend/           # FastAPI API server
│   └── app/
│       ├── api/       # Route handlers
│       ├── core/      # Config, database
│       ├── models/    # SQLAlchemy models
│       └── schemas/   # Pydantic schemas
├── worker/            # Celery ML worker
│   └── tasks/
│       ├── protect.py     # Main task
│       ├── pgd_attack.py  # Adversarial attack
│       └── chunker.py     # Audio splitting
└── docker-compose.yml
```

---

## 🎯 Measured Results (not targets)

LibriSpeech dev-clean benchmark, 10 speakers / 60 clips (`evaluation/end_to_end_validation.md`):

| Metric | Measured |
|---|---|
| L∞ perturbation | ≤ 0.020000 |
| SNR / SI-SDR | 17.02 / 16.99 dB |
| STOI | 0.9191 |
| HuBERT Layer-12 cos-sim (orig→prot) | 0.2497 |
| ECAPA orig↔orig / orig↔prot / orig↔other | 0.7641 / 0.6769 / 0.1102 |

Downstream voice-cloning (XTTS-v2, ECAPA source→clone): baseline clones 0.55–0.60; protected clones 0.33–0.39; unrelated control ≈ 0.09. Paired replication (300 clones, 3 refs × 3 PGD seeds): mean Δ ≈ 0.19–0.22 per seed, 95% CIs exclude zero, 10/10 speakers positive on all seeds. **Voice-cloning validation: PRELIMINARY (single engine).** No "prevents cloning" claim is made.

---

## 📋 Roadmap

- [x] **Phase 1 (MVP)** - CLI tool, PGD attack, chunking
- [x] **Web interface** - Next.js UI, auth, upload/status/download, vault
- [x] **Benchmark** - LibriSpeech engineering/ML/speaker-quality validation
- [x] **Cloning evaluation (preliminary)** - XTTS-v2 baseline + paired replication
- [ ] **Multi-engine replication** - Bark, VALL-E X, OpenVoice
- [ ] **Subjective MOS listening tests** (objective STOI/SNR only so far)
- [ ] **Phase 3 (V1.0)** - Psychoacoustic masking, batch uploads

---

## ⚠️ Disclaimer

Protection is not 100% guaranteed. AudioShield provides a technical barrier against current AI voice cloning methods but cannot guarantee protection against future model architectures.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Built with ❤️ by Sarthak**
