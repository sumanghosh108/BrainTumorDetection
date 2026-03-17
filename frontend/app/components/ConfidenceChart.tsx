"use client";

import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface ConfidenceChartProps {
  prediction: {
    tumor_type: string;
    confidence: number;
  };
}

const TUMOR_LABELS = ["Glioma", "Meningioma", "No Tumor", "Pituitary"];
const TUMOR_KEYS = ["glioma", "meningioma", "no_tumor", "pituitary"];
const COLORS = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6"];

export default function ConfidenceChart({ prediction }: ConfidenceChartProps) {
  // Build probability bars — highlight the predicted class
  const values = TUMOR_KEYS.map((key) =>
    key === prediction.tumor_type ? prediction.confidence * 100 : 0
  );

  return (
    <div className="bg-white rounded-lg p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-700 mb-2">
        Classification Confidence
      </h3>
      <Plot
        data={[
          {
            x: TUMOR_LABELS,
            y: values,
            type: "bar",
            marker: { color: COLORS },
            text: values.map((v) => `${v.toFixed(1)}%`),
            textposition: "auto",
          },
        ]}
        layout={{
          height: 260,
          margin: { t: 10, b: 40, l: 40, r: 10 },
          yaxis: { range: [0, 100], title: "Confidence (%)" },
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { size: 12 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        className="w-full"
      />
    </div>
  );
}
