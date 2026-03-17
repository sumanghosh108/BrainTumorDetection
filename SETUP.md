# Setup & Run from Scratch

Complete instructions to get the Brain Tumor AI Diagnostic Platform running on your local machine.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Git | any | `git --version` |
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | v2+ | `docker compose version` |

---

## Option A: Docker Compose (Recommended)

This spins up everything — backend, frontend, database, Prometheus, Grafana — in one command.

### Step 1: Clone & configure environment

```bash
git clone <your-repo-url> brain-tumor-ai-platform
cd brain-tumor-ai-platform

# Create .env from template
cp .env.example .env
```

Edit `.env` and fill in **at minimum**:

```env
# These are required for the app to start:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/brain_tumor
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET=brain-tumor-scans

FIREBASE_CREDENTIALS=firebase-credentials.json

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
```

### Step 2: Add Firebase credentials

Place your Firebase Admin SDK JSON file in the project root:

```bash
# Download from Firebase Console > Project Settings > Service Accounts > Generate New Private Key
cp ~/Downloads/your-firebase-adminsdk.json ./firebase-credentials.json
```

### Step 3: Add model weights (optional for first run)

Place trained `.pt` files in `weights/`:

```
weights/
├── yolov8_brain_tumor.pt    # YOLOv8 detection
├── cnn.pt                   # Custom CNN classifier
├── vgg16.pt                 # VGG-16 classifier
├── vgg19.pt                 # VGG-19 classifier
└── resnet101.pt             # ResNet-101 classifier
```

> The app starts without weights — it logs warnings and returns 503 on `/predict` until weights are provided.

### Step 4: Build & run

```bash
cd infrastructure
docker compose up --build
```

First build takes 5-10 minutes (PyTorch is large). Subsequent starts are fast.

### Step 5: Verify

| Service | URL | Expected |
|---------|-----|----------|
| Frontend | http://localhost:3000 | Landing page |
| Backend API | http://localhost:8000/health | `{"status":"ok"}` |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive API docs |
| Prometheus | http://localhost:9090 | Prometheus UI |
| Grafana | http://localhost:3001 | Login: `admin` / `admin` |

---

## Option B: Run Locally (without Docker)

### Step 1: Database

Start PostgreSQL (use Docker just for the DB, or a local install):

```bash
docker run -d \
  --name bt-postgres \
  -e POSTGRES_DB=brain_tumor \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine
```

Wait 5 seconds, then apply the schema:

```bash
docker exec -i bt-postgres psql -U postgres -d brain_tumor < backend/database/migrations/001_initial.sql
```

### Step 2: Backend

```bash
# Create virtual environment
cd backend
python -m venv venv

# Activate (choose your OS):
# Linux/Mac:
source venv/bin/activate
# Windows (Git Bash):
source venv/Scripts/activate
# Windows (cmd):
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env — set DATABASE_URL to:
#   postgresql+asyncpg://postgres:postgres@localhost:5432/brain_tumor

# Run the server
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
INFO     app_startup_begin
INFO     database_warmup_ok
WARNING  s3_warmup_failed — continuing without S3 pre-check
INFO     ai_models_loaded  (or ai_model_load_failed if no weights)
INFO     app_startup_complete
INFO     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Frontend

Open a new terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Open http://localhost:3000.

---

## Quick Smoke Test (curl)

After the backend is running, test without the frontend:

```bash
# 1. Health check
curl http://localhost:8000/health
# → {"status":"ok"}

# 2. Swagger docs
# Open http://localhost:8000/docs in a browser

# 3. Upload a scan (requires Firebase token)
# Get a token from your Firebase client, then:
TOKEN="your-firebase-id-token"

curl -X POST http://localhost:8000/api/v1/scan/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/brain_mri.png"
# → {"scan_id":"...","s3_url":"...","status":"uploaded",...}

# 4. Run prediction
SCAN_ID="the-scan-id-from-step-3"

curl -X POST http://localhost:8000/api/v1/scan/$SCAN_ID/predict \
  -H "Authorization: Bearer $TOKEN"
# → {"scan_id":"...","status":"completed","prediction":{...},...}

# 5. Get full result
curl http://localhost:8000/api/v1/scan/$SCAN_ID/result \
  -H "Authorization: Bearer $TOKEN"
```

---

## Development Tips

### Hot reload

- **Backend**: `--reload` flag on uvicorn watches for file changes.
- **Frontend**: `npm run dev` has hot reload built in.

### Skip auth for local dev

To test without Firebase, temporarily comment out the `Depends(get_current_user)` in `backend/api/routes/scan.py` and hardcode a test user ID.

### Run without S3

The app gracefully handles S3 being unavailable at startup. For local testing without AWS:
1. The upload endpoint will fail (expected).
2. To test the AI pipeline directly, write a small script:

```python
from backend.ai_models.ensemble_model import EnsembleModel

model = EnsembleModel()
model.load_all()

with open("test_mri.png", "rb") as f:
    result = model.predict(f.read())

print(result.tumor_type, result.confidence)
```

### Run only monitoring

```bash
cd infrastructure
docker compose up prometheus grafana
```

---

## Folder Cheat Sheet

```
.
├── backend/              ← Python (FastAPI + AI)
│   ├── main.py           ← Entry point: uvicorn backend.main:app
│   ├── ai_models/        ← YOLO + CNN + VGG16 + VGG19 + ResNet101 + Ensemble
│   ├── explainability/   ← Grad-CAM heatmap generation
│   ├── report/           ← Radiology report generator
│   ├── api/routes/       ← REST endpoints
│   ├── database/         ← ORM models + migrations
│   └── services/         ← S3, Firebase auth
├── frontend/             ← Next.js 14 + Tailwind
├── infrastructure/       ← Docker, docker-compose, deploy script
├── monitoring/           ← Prometheus + Grafana configs
├── weights/              ← Place .pt model files here
└── docs/                 ← Architecture, API docs, deployment guide
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'backend'` | Run uvicorn from the project root, not inside `backend/` |
| `Connection refused` on database | Ensure Postgres is running: `docker ps` |
| `s3_warmup_failed` warning | Normal without AWS creds — upload/predict will fail, but app starts |
| `ai_model_load_failed` | Weights not found in `weights/` — predictions return 503 |
| PyTorch OOM on t2.micro | Add 2GB swap: see `docs/deployment.md` section 4d |
| Frontend can't reach backend | Check `NEXT_PUBLIC_API_URL` in `.env.local` and CORS in backend `.env` |
| `firebase_token_invalid` | Ensure `firebase-credentials.json` exists and matches your Firebase project |
| Docker build fails on ARM Mac | Add `platform: linux/amd64` to backend service in docker-compose.yml |
