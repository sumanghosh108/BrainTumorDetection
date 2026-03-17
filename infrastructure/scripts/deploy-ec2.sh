#!/usr/bin/env bash
# ============================================================
# deploy-ec2.sh — Deploy the Brain Tumor AI Platform to an
# EC2 t2.micro instance via SSH.
#
# Prerequisites:
#   1. EC2 instance running Amazon Linux 2023 / Ubuntu 22.04
#   2. Docker + Docker Compose installed on the instance
#   3. SSH key configured (~/.ssh/bt-platform.pem)
#   4. Security group allows ports 22, 80, 443, 3000, 8000
#
# Usage:
#   ./deploy-ec2.sh <EC2_PUBLIC_IP> [SSH_KEY_PATH]
# ============================================================

set -euo pipefail

EC2_IP="${1:?Usage: ./deploy-ec2.sh <EC2_IP> [SSH_KEY]}"
SSH_KEY="${2:-$HOME/.ssh/bt-platform.pem}"
REMOTE_DIR="/home/ec2-user/brain-tumor-ai-platform"
SSH_OPTS="-o StrictHostKeyChecking=no -i $SSH_KEY"

echo "==> Syncing project to $EC2_IP:$REMOTE_DIR ..."
rsync -avz --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' \
  --exclude '.git' --exclude 'venv' \
  -e "ssh $SSH_OPTS" \
  "$(dirname "$0")/../../" "ec2-user@${EC2_IP}:${REMOTE_DIR}/"

echo "==> Building and starting services on EC2 ..."
ssh $SSH_OPTS "ec2-user@${EC2_IP}" <<'REMOTE'
  set -euo pipefail
  cd brain-tumor-ai-platform/infrastructure

  # Pull latest images and rebuild
  docker compose pull postgres prometheus grafana
  docker compose build --parallel backend frontend
  docker compose up -d

  echo "==> Services running:"
  docker compose ps
REMOTE

echo ""
echo "=== Deployment complete ==="
echo "  Frontend : http://${EC2_IP}:3000"
echo "  Backend  : http://${EC2_IP}:8000/health"
echo "  Grafana  : http://${EC2_IP}:3001  (admin/admin)"
echo "  Prometheus: http://${EC2_IP}:9090"
