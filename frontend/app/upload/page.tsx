"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import UploadDropzone from "@/app/components/UploadDropzone";
import type { PredictionResponse } from "@/app/services/api";

export default function UploadPage() {
  const router = useRouter();
  const [scanId, setScanId] = useState<string | null>(null);

  function handlePrediction(data: PredictionResponse) {
    setScanId(data.scan_id);
    // Navigate to results after a short delay so the user sees the success state
    setTimeout(() => {
      router.push(`/results?scan=${data.scan_id}`);
    }, 1500);
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Upload MRI Scan</h1>
      <p className="text-slate-500 mb-8">
        Upload a brain MRI image for AI-powered tumor detection and analysis.
      </p>

      <UploadDropzone
        onUploadComplete={(u) => setScanId(u.scan_id)}
        onPredictionComplete={handlePrediction}
      />

      {scanId && (
        <p className="mt-4 text-xs text-slate-400 text-center">
          Scan ID: {scanId}
        </p>
      )}
    </div>
  );
}
