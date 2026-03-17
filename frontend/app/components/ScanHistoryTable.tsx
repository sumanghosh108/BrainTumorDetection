"use client";

import Link from "next/link";
import { format } from "date-fns";
import type { ScanHistory } from "@/app/services/api";

interface ScanHistoryTableProps {
  scans: ScanHistory[];
}

const STATUS_COLORS: Record<string, string> = {
  uploaded: "bg-blue-100 text-blue-700",
  processing: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function ScanHistoryTable({ scans }: ScanHistoryTableProps) {
  if (scans.length === 0) {
    return (
      <p className="text-slate-500 text-sm py-8 text-center">
        No scan history found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3">Tumor Type</th>
            <th className="px-4 py-3">Confidence</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {scans.map((scan) => (
            <tr key={scan.scan_id} className="hover:bg-slate-50">
              <td className="px-4 py-3 whitespace-nowrap">
                {format(new Date(scan.scan_date), "PP")}
              </td>
              <td className="px-4 py-3 capitalize">
                {scan.tumor_type?.replace("_", " ") ?? "—"}
              </td>
              <td className="px-4 py-3">
                {scan.confidence != null
                  ? `${(scan.confidence * 100).toFixed(1)}%`
                  : "—"}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    STATUS_COLORS[scan.status] ?? ""
                  }`}
                >
                  {scan.status}
                </span>
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/results?scan=${scan.scan_id}`}
                  className="text-primary-600 hover:underline text-xs"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
