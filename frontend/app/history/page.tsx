"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getPatientHistory } from "@/app/services/api";
import type { ScanHistory } from "@/app/services/api";
import ScanHistoryTable from "@/app/components/ScanHistoryTable";

function HistoryContent() {
  const searchParams = useSearchParams();
  const patientId = searchParams.get("patient");
  const [scans, setScans] = useState<ScanHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = patientId || localStorage.getItem("patient_id");
    if (!id) {
      setLoading(false);
      return;
    }
    getPatientHistory(id)
      .then(setScans)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId]);

  if (loading) {
    return <p className="text-slate-500 text-center py-8">Loading...</p>;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm">
      <ScanHistoryTable scans={scans} />
    </div>
  );
}

export default function HistoryPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Scan History</h1>
      <Suspense fallback={<p className="text-slate-500">Loading...</p>}>
        <HistoryContent />
      </Suspense>
    </div>
  );
}
