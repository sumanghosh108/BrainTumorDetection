"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getScanResult } from "@/app/services/api";
import type { FullResultResponse } from "@/app/services/api";
import MriViewer from "@/app/components/MriViewer";
import ConfidenceChart from "@/app/components/ConfidenceChart";
import ReportPanel from "@/app/components/ReportPanel";

function ResultsContent() {
  const searchParams = useSearchParams();
  const scanId = searchParams.get("scan");
  const [result, setResult] = useState<FullResultResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!scanId) return;
    getScanResult(scanId)
      .then(setResult)
      .catch((err) => setError(err.message));
  }, [scanId]);

  if (!scanId) {
    return <p className="text-slate-500">No scan ID provided.</p>;
  }

  if (error) {
    return <p className="text-red-600">{error}</p>;
  }

  if (!result) {
    return <p className="text-slate-500">Loading results...</p>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left column — MRI + heatmap */}
      <div className="space-y-4">
        <MriViewer
          scanUrl={result.s3_url}
          gradcamUrl={result.prediction ? result.report?.gradcam_url : null}
        />
        {result.prediction && <ConfidenceChart prediction={result.prediction} />}
      </div>

      {/* Right column — Report */}
      <div>
        {result.report ? (
          <ReportPanel report={result.report} />
        ) : (
          <div className="bg-white rounded-lg p-6 shadow-sm text-center text-slate-500">
            Prediction not yet available.
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Scan Results</h1>
      <Suspense fallback={<p className="text-slate-500">Loading...</p>}>
        <ResultsContent />
      </Suspense>
    </div>
  );
}
