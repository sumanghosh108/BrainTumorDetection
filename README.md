# Brain Tumor AI Diagnostic Platform

A production-grade, full-stack healthcare SaaS platform for AI-powered brain tumor detection from MRI scans. Features a weighted ensemble of four deep learning classifiers, YOLOv8 tumor localisation, Grad-CAM explainability overlays, and structured radiology report generation.

---

## AI Pipeline

```
MRI Upload → S3 → YOLOv8 Detection → Region Crop →
┌─────────────────────────────────────────────────┐
│  CNN (0.15) + VGG-16 (0.25) + VGG-19 (0.25)    │
│            + ResNet-101 (0.35)                   │
│         Weighted Ensemble Average                │
└─────────────────────────────────────────────────┘
→ Grad-CAM Heatmap → Radiology Report
```

### Model Performance

| Model | Training Acc. | Validation Acc. | Test Acc. | Ensemble Weight |
|-----------|-----------|------------|----------|---------|
| CNN | 99.33% | 86.71% | 96.01% | 0.15 |
| VGG-16 | 100% | 95.71% | 98.71% | 0.25 |
| VGG-19 | 100% | 95.79% | 98.74% | 0.25 |
| ResNet-101 | 90.84% | 80.28% | 88.58% | 0.35 |

The weighted ensemble combines all four classifiers to reduce misclassification on edge cases. Weights are tunable via environment variables.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TailwindCSS, Plotly, react-dropzone |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| AI/ML | PyTorch, YOLOv8 (Ultralytics), TorchVision, pytorch-grad-cam |
| Database | Supabase (PostgreSQL), SQLAlchemy async ORM |
| Auth | Firebase Authentication |
| Storage | AWS S3 (pre-signed URLs) |
| Monitoring | Prometheus + Grafana (7-panel dashboard) |
| Infra | Docker Compose, EC2 (t2.micro Free Tier) |

---

## Project Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/routes/scan.py       # REST endpoints (upload, predict, result, history)
│   ├── ai_models/
│   │   ├── yolo_detector.py     # YOLOv8 tumor localisation
│   │   ├── cnn_classifier.py    # CNN, VGG-16, VGG-19, ResNet-101 wrappers
│   │   ├── ensemble_model.py    # Weighted ensemble pipeline
│   │   └── preprocessing.py     # Image loading, letterbox, crop, transforms
│   ├── explainability/
│   │   └── gradcam.py           # Grad-CAM heatmap overlay generation
│   ├── report/
│   │   └── radiology_report.py  # Structured clinical report generator
│   ├── database/
│   │   ├── models.py            # ORM: Patient, Scan, Prediction, Report, AuditLog
│   │   ├── db.py                # Async engine + Supabase client
│   │   └── migrations/          # PostgreSQL DDL
│   ├── services/                # S3 storage, Firebase auth
│   ├── middleware/              # Request logging, request_id tracking
│   └── utils/                   # Structured logger, audit trail
├── frontend/
│   └── app/
│       ├── upload/              # Drag-and-drop MRI upload
│       ├── results/             # MRI viewer + Grad-CAM toggle + report panel
│       ├── dashboard/           # Scan history overview
│       └── components/          # MriViewer, ConfidenceChart, ReportPanel, etc.
├── infrastructure/
│   ├── docker-compose.yml       # 5 services: backend, frontend, postgres, prometheus, grafana
│   ├── docker/                  # Multi-stage Dockerfiles
│   └── scripts/deploy-ec2.sh   # One-command EC2 deployment
├── monitoring/
│   ├── prometheus/              # Scrape config
│   └── grafana/                 # Dashboard JSON + provisioning
├── weights/                     # Place trained .pt model files here
└── docs/
    ├── architecture.md          # System diagrams + design decisions
    ├── api_docs.md              # Full endpoint documentation
    └── deployment.md            # Step-by-step deployment guide
```

---

## Quick Start

### Prerequisites

- Python 3.11+, Node.js 20+, Docker & Docker Compose v2+

### Option 1: Docker Compose (recommended)

```bash
# 1. Clone and configure
git clone https://github.com/sumanghosh108/BrainTumorDetection.git
cd BrainTumorDetection
cp .env.example .env          # edit with your keys

# 2. Add Firebase service account
cp ~/Downloads/firebase-adminsdk.json ./firebase-credentials.json

# 3. (Optional) Add model weights to weights/

# 4. Build and run
cd infrastructure
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/health |
| Swagger Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin/admin) |
| Prometheus | http://localhost:9090 |

### Option 2: Local development

```bash
# Terminal 1 — Database
docker run -d --name bt-postgres \
  -e POSTGRES_DB=brain_tumor -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:16-alpine
docker exec -i bt-postgres psql -U postgres -d brain_tumor \
  < backend/database/migrations/001_initial.sql

# Terminal 2 — Backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env              # edit DATABASE_URL
uvicorn backend.main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend && npm install
cp .env.example .env.local                        # edit NEXT_PUBLIC_API_URL
npm run dev
```

See [SETUP.md](SETUP.md) for detailed instructions, smoke tests, and troubleshooting.

---

## API Endpoints

All endpoints (except `/health`) require a Firebase ID token:
```
Authorization: Bearer <firebase_id_token>
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scan/upload` | Upload MRI scan to S3 |
| `POST` | `/api/v1/scan/{scan_id}/predict` | Run AI pipeline (YOLO + ensemble + Grad-CAM) |
| `GET` | `/api/v1/scan/{scan_id}/result` | Full result with prediction + radiology report |
| `GET` | `/api/v1/patient/{patient_id}/history` | Patient scan history |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

See [docs/api_docs.md](docs/api_docs.md) for request/response examples.

---

## Radiology Report Schema

```json
{
  "patient_id": "uuid",
  "scan_date": "2026-03-17T12:00:00Z",
  "tumor_type": "glioma",
  "confidence": 0.94,
  "location": "Right parietal/temporal region",
  "size_estimate": "2.3 cm (estimated)",
  "gradcam_url": "https://bucket.s3.amazonaws.com/gradcam/.../overlay.png",
  "recommendation": "Findings are consistent with a glioma. Urgent referral to neuro-oncology is recommended..."
}
```

---

## Deployment

The platform is designed for **AWS Free Tier**:

- **Frontend** → Vercel (free hobby tier)
- **Backend + AI** → EC2 t2.micro with Docker Compose
- **Database** → Supabase free tier
- **Storage** → S3 (5 GB free)

One-command deploy to EC2:
```bash
./infrastructure/scripts/deploy-ec2.sh <EC2_IP> ~/.ssh/your-key.pem
```

See [docs/deployment.md](docs/deployment.md) for the full step-by-step guide.

---

## Research Background

### Problem

Traditional brain tumor detection relies on manual MRI interpretation, which is time-consuming, subjective, and prone to inter-observer variability. Early-stage tumors can be missed, and access to specialist neuroradiologists is limited globally.

### Approach

This project applies a multi-model deep learning ensemble to automate tumor detection and classification into four categories: **glioma**, **meningioma**, **pituitary adenoma**, and **no tumor**. YOLOv8 first localises the tumor region, then four classification backbones (CNN, VGG-16, VGG-19, ResNet-101) vote via weighted probability averaging. Grad-CAM provides visual explanations to build clinician trust.

### Dataset

- **19,374** augmented MRI images (PNG, 256x256x3)
- **Binary split**: 9,828 tumor / 9,546 no-tumor
- **Augmentation**: rotation, flipping, scaling to address class imbalance and limited data availability
- **Split**: 70% training / 20% validation / 10% testing

### Key Results

| Metric | CNN | VGG-16 | VGG-19 | ResNet-101 |
|--------|-----|--------|--------|------------|
| Test Accuracy | 96.01% | 98.71% | 98.74% | 88.58% |
| Precision (Tumor) | 0.96 | 1.00 | 1.00 | 0.88 |
| Recall (Tumor) | 0.95 | 0.97 | 0.97 | 0.86 |
| F1-Score (Tumor) | 0.96 | 0.99 | 0.99 | 0.87 |

VGG-19 achieved the highest individual accuracy (98.74%). The weighted ensemble leverages ResNet-101's architectural depth (highest weight at 0.35) alongside VGG's precision to produce robust predictions across diverse tumor presentations.

### Future Work

- Train on larger, multi-institutional datasets to reduce overfitting
- Add multi-class tumour grading (WHO Grade I-IV)
- Integrate DICOM support for direct PACS connectivity
- Add 3D volumetric analysis from full MRI sequences

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
