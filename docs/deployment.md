# Deployment Guide

Step-by-step instructions to deploy the Brain Tumor AI Diagnostic Platform using **Vercel** (frontend), **EC2 t2.micro** (backend + AI), **S3** (storage), and **Supabase** (database).

---

## Prerequisites

- AWS account (Free Tier eligible)
- Vercel account (free hobby tier)
- Supabase project (free tier)
- Firebase project with Authentication enabled
- Docker + Docker Compose installed locally
- Trained model weights (`.pt` files)

---

## 1. Supabase (PostgreSQL)

1. Create a new Supabase project at [supabase.com](https://supabase.com).
2. Open the **SQL Editor** and run `backend/database/migrations/001_initial.sql`.
3. Copy the connection string from **Settings > Database > Connection string > URI** (use the `postgresql://` variant).
4. Copy the **service role key** from **Settings > API > service_role**.
5. Store both values:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres
   SUPABASE_URL=https://[ref].supabase.co
   SUPABASE_SERVICE_KEY=eyJ...
   ```

---

## 2. AWS S3 Bucket

1. Create an S3 bucket (e.g., `brain-tumor-scans`).
2. **Block all public access** — the backend uses pre-signed URLs.
3. Create an IAM user with `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on the bucket ARN.
4. Grab the access key and secret:
   ```
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-1
   S3_BUCKET=brain-tumor-scans
   ```
5. Enable **server-side encryption (SSE-S3)** as default on the bucket.

---

## 3. Firebase Authentication

1. Go to the [Firebase Console](https://console.firebase.google.com), create a project.
2. Enable **Email/Password** and/or **Google Sign-In** providers.
3. Download the **service account JSON** → save as `firebase-credentials.json`.
4. From **Project Settings > General**, copy the web app config:
   ```
   NEXT_PUBLIC_FIREBASE_API_KEY=...
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project
   ```

---

## 4. EC2 Instance (Backend)

### 4a. Launch Instance

1. Launch a **t2.micro** (Free Tier) with **Amazon Linux 2023** or **Ubuntu 22.04**.
2. Security group — inbound rules:
   | Port  | Source    | Purpose         |
   |-------|-----------|-----------------|
   | 22    | Your IP   | SSH             |
   | 8000  | 0.0.0.0/0 | Backend API     |
   | 9090  | Your IP   | Prometheus      |
   | 3001  | Your IP   | Grafana         |
3. Allocate and associate an **Elastic IP** (free while instance is running).

### 4b. Install Docker

```bash
# Amazon Linux 2023
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

### 4c. Deploy

1. Copy your `.env` file to the EC2 instance.
2. Upload model weights to `/home/ec2-user/brain-tumor-ai-platform/weights/`.
3. Run the deploy script:
   ```bash
   chmod +x infrastructure/scripts/deploy-ec2.sh
   ./infrastructure/scripts/deploy-ec2.sh <EC2_ELASTIC_IP> ~/.ssh/your-key.pem
   ```
4. Verify: `curl http://<EC2_IP>:8000/health` → `{"status":"ok"}`

### 4d. Swap File (recommended for t2.micro)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

This is critical — PyTorch model loading can exceed 1 GB RAM on t2.micro.

---

## 5. Vercel (Frontend)

1. Push the repo to GitHub.
2. Import the project in [Vercel](https://vercel.com/new).
3. Set **Root Directory** to `frontend`.
4. Add environment variables:
   ```
   NEXT_PUBLIC_API_URL=http://<EC2_ELASTIC_IP>:8000
   NEXT_PUBLIC_FIREBASE_API_KEY=...
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
   ```
5. Deploy. Vercel auto-detects Next.js and builds with `output: "standalone"`.

> For production, put the EC2 backend behind an HTTPS reverse proxy (Caddy or nginx with Let's Encrypt) and update `NEXT_PUBLIC_API_URL` to use `https://`.

---

## 6. Model Weights

Place your trained `.pt` files in the `weights/` directory on EC2:

```
weights/
├── yolov8_brain_tumor.pt    # YOLOv8 detection model
├── cnn.pt                   # Custom lightweight CNN
├── vgg16.pt                 # VGG-16 classifier head
├── vgg19.pt                 # VGG-19 classifier head
└── resnet101.pt             # ResNet-101 classifier head
```

If weights are missing at startup, the app logs a warning and starts anyway. Prediction endpoints will return 503 until weights are provided.

---

## 7. Monitoring

- **Prometheus**: `http://<EC2_IP>:9090` — pre-configured to scrape the backend `/metrics` endpoint.
- **Grafana**: `http://<EC2_IP>:3001` — login `admin/admin`, dashboard "Brain Tumor AI Platform" is auto-provisioned.

---

## 8. Production Checklist

- [ ] HTTPS via Caddy/nginx reverse proxy with Let's Encrypt
- [ ] Change Grafana default password
- [ ] Restrict Prometheus/Grafana ports to VPN or internal only
- [ ] Set `LOG_LEVEL=WARNING` in production `.env`
- [ ] Enable S3 bucket versioning for audit trail
- [ ] Configure CloudWatch alarms for EC2 CPU / memory
- [ ] Set up daily database backups (Supabase handles this on paid plans)
- [ ] Rate-limit the `/predict` endpoint (one concurrent prediction per user)
