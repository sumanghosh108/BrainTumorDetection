import axios from "axios";
import { auth } from "@/app/lib/firebase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000, // 2 min — inference can be slow on CPU
});

// Attach Firebase ID token to every request
api.interceptors.request.use(async (config) => {
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------- Types ----------

export interface UploadResponse {
  scan_id: string;
  s3_url: string;
  status: string;
  uploaded_at: string;
}

export interface PredictionResult {
  tumor_type: string;
  confidence: number;
  location: string | null;
  size_estimate: string | null;
}

export interface RadiologyReport {
  report_id: string;
  patient_id: string;
  scan_id: string;
  scan_date: string;
  tumor_type: string;
  confidence: number;
  location: string | null;
  size_estimate: string | null;
  gradcam_url: string | null;
  recommendation: string;
  generated_at: string;
}

export interface PredictionResponse {
  scan_id: string;
  status: string;
  prediction: PredictionResult;
  gradcam_url: string | null;
  processing_time_ms: number;
  predicted_at: string;
}

export interface FullResultResponse {
  scan_id: string;
  patient_id: string;
  s3_url: string;
  status: string;
  prediction: PredictionResult | null;
  report: RadiologyReport | null;
  uploaded_at: string;
  completed_at: string | null;
}

export interface ScanHistory {
  scan_id: string;
  scan_date: string;
  tumor_type: string | null;
  confidence: number | null;
  status: string;
  s3_url: string;
}

// ---------- API calls ----------

export async function uploadScan(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<UploadResponse>("/api/v1/scan/upload", form);
  return data;
}

export async function predictScan(scanId: string): Promise<PredictionResponse> {
  const { data } = await api.post<PredictionResponse>(
    `/api/v1/scan/${scanId}/predict`
  );
  return data;
}

export async function getScanResult(
  scanId: string
): Promise<FullResultResponse> {
  const { data } = await api.get<FullResultResponse>(
    `/api/v1/scan/${scanId}/result`
  );
  return data;
}

export async function getPatientHistory(
  patientId: string
): Promise<ScanHistory[]> {
  const { data } = await api.get<ScanHistory[]>(
    `/api/v1/patient/${patientId}/history`
  );
  return data;
}

export default api;
