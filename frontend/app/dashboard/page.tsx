"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPatientHistory } from "@/app/services/api";
import type { ScanHistory } from "@/app/services/api";
import ScanHistoryTable from "@/app/components/ScanHistoryTable";

export default function DashboardPage() {
  const [scans, setScans] = useState<ScanHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Replace with real patient ID from auth context
    const patientId = localStorage.getItem("patient_id");
    if (!patientId) {
      setLoading(false);
      return;
    }
    getPatientHistory(patientId)
      .then(setScans)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <Link
          href="/upload"
          className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          New Scan
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow-sm">
        {loading ? (
          <p className="p-8 text-center text-slate-500">Loading history...</p>
        ) : (
          <ScanHistoryTable scans={scans} />
        )}
      </div>
    </div>
  );
}
