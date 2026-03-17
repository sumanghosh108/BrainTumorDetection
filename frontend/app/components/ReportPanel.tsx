"use client";

import type { RadiologyReport } from "@/app/services/api";
import { format } from "date-fns";

interface ReportPanelProps {
  report: RadiologyReport;
}

const SEVERITY_MAP: Record<string, { label: string; color: string }> = {
  glioma: { label: "High Severity", color: "bg-red-100 text-red-800" },
  meningioma: { label: "Moderate", color: "bg-amber-100 text-amber-800" },
  pituitary: { label: "Moderate", color: "bg-amber-100 text-amber-800" },
  no_tumor: { label: "Normal", color: "bg-green-100 text-green-800" },
};

export default function ReportPanel({ report }: ReportPanelProps) {
  const severity = SEVERITY_MAP[report.tumor_type] ?? SEVERITY_MAP.no_tumor;

  return (
    <div className="bg-white rounded-lg shadow-sm divide-y divide-slate-100">
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">Radiology Report</h3>
        <span
          className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${severity.color}`}
        >
          {severity.label}
        </span>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3 text-sm">
        <Row label="Scan Date" value={format(new Date(report.scan_date), "PPp")} />
        <Row
          label="Tumor Type"
          value={report.tumor_type.replace("_", " ").toUpperCase()}
        />
        <Row
          label="Confidence"
          value={`${(report.confidence * 100).toFixed(1)}%`}
        />
        {report.location && <Row label="Location" value={report.location} />}
        {report.size_estimate && (
          <Row label="Size Estimate" value={report.size_estimate} />
        )}
      </div>

      {/* Recommendation */}
      <div className="p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
          Recommendation
        </p>
        <p className="text-sm text-slate-700 leading-relaxed">
          {report.recommendation}
        </p>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{value}</span>
    </div>
  );
}
