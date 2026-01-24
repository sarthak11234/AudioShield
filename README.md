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

- **Drag & Drop Upload** - Simple interface for .wav/.mp3/.flac files
- **Real-time Status** - Track processing progress
- **Imperceptible Protection** - 0.02% noise (MOS > 4.0)
- **Privacy First** - Files auto-deleted after 1 hour
- **GPU Optimized** - Designed for 6GB VRAM (RTX 3060/4050)

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
- Python 3.10+
- Node.js 18+
- Docker Desktop
- NVIDIA GPU (6GB+ VRAM recommended)

### 1. Start Infrastructure
```bash
docker compose up -d
```

### 2. Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Worker
```bash
cd worker
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
celery -A celery_app worker --pool=solo
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/upload` | Upload audio file |
| GET | `/api/status/{id}` | Get task status |
| GET | `/api/download/{id}` | Download protected file |

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

## 🎯 Success Metrics

| Metric | Target |
|--------|--------|
| AI Cloning Disruption | >80% |
| Audio Quality (MOS) | >4.0 |
| Processing Time (3-min song) | <2 min |

---

## 📋 Roadmap

- [x] **Phase 1 (MVP)** - CLI tool, PGD attack, chunking
- [ ] **Phase 2 (Beta)** - Web interface, full song support
- [ ] **Phase 3 (V1.0)** - Psychoacoustic masking, batch uploads

---

## ⚠️ Disclaimer

Protection is not 100% guaranteed. AudioShield provides a technical barrier against current AI voice cloning methods but cannot guarantee protection against future model architectures.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Built with ❤️ by Sarthak**
