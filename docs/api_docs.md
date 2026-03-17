# API Documentation

Base URL: `http://localhost:8000` (dev) or `https://your-ec2-ip:8000` (prod)

All endpoints except `/health` and `/metrics` require a Firebase ID token in the `Authorization` header:
```
Authorization: Bearer <firebase_id_token>
```

---

## POST /api/v1/scan/upload

Upload an MRI scan image.

**Request**: `multipart/form-data`
| Field | Type   | Description             |
|-------|--------|-------------------------|
| file  | File   | MRI image (PNG, JPEG, DICOM) |

**Response** `201`:
```json
{
  "scan_id": "uuid",
  "s3_url": "https://bucket.s3.region.amazonaws.com/scans/...",
  "status": "uploaded",
  "uploaded_at": "2026-03-17T12:00:00Z"
}
```

---

## POST /api/v1/scan/{scan_id}/predict

Trigger AI inference on an uploaded scan.

**Response** `200`:
```json
{
  "scan_id": "uuid",
  "status": "completed",
  "prediction": {
    "tumor_type": "glioma",
    "confidence": 0.94,
    "location": "Right parietal/temporal region",
    "size_estimate": "2.3 cm (estimated)"
  },
  "gradcam_url": "https://bucket.s3.region.amazonaws.com/gradcam/.../overlay.png",
  "processing_time_ms": 1250.42,
  "predicted_at": "2026-03-17T12:00:05Z"
}
```

**Errors**:
- `404` — Scan not found
- `409` — Prediction already exists
- `503` — AI models not loaded

---

## GET /api/v1/scan/{scan_id}/result

Retrieve full results including the radiology report.

**Response** `200`:
```json
{
  "scan_id": "uuid",
  "patient_id": "uuid",
  "s3_url": "...",
  "status": "completed",
  "prediction": { ... },
  "report": {
    "report_id": "uuid",
    "patient_id": "uuid",
    "scan_id": "uuid",
    "scan_date": "2026-03-17T12:00:00Z",
    "tumor_type": "glioma",
    "confidence": 0.94,
    "location": "Right parietal/temporal region",
    "size_estimate": "2.3 cm (estimated)",
    "gradcam_url": "...",
    "recommendation": "Findings are consistent with a glioma...",
    "generated_at": "2026-03-17T12:00:05Z"
  },
  "uploaded_at": "2026-03-17T12:00:00Z",
  "completed_at": "2026-03-17T12:00:05Z"
}
```

---

## GET /api/v1/patient/{patient_id}/history

List all scans for a patient, most recent first.

**Response** `200`:
```json
[
  {
    "scan_id": "uuid",
    "scan_date": "2026-03-17T12:00:00Z",
    "tumor_type": "glioma",
    "confidence": 0.94,
    "status": "completed",
    "s3_url": "..."
  }
]
```

---

## GET /health

Health check (no auth required).

**Response** `200`: `{"status": "ok"}`

---

## GET /metrics

Prometheus metrics endpoint (no auth required).
