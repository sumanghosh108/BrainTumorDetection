"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadScan, predictScan } from "@/app/services/api";
import type { PredictionResponse, UploadResponse } from "@/app/services/api";

interface UploadDropzoneProps {
  onUploadComplete?: (data: UploadResponse) => void;
  onPredictionComplete?: (data: PredictionResponse) => void;
  onError?: (error: string) => void;
}

type Stage = "idle" | "uploading" | "predicting" | "done" | "error";

export default function UploadDropzone({
  onUploadComplete,
  onPredictionComplete,
  onError,
}: UploadDropzoneProps) {
  const [stage, setStage] = useState<Stage>("idle");
  const [message, setMessage] = useState("");

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      try {
        // Upload
        setStage("uploading");
        setMessage(`Uploading ${file.name}...`);
        const upload = await uploadScan(file);
        onUploadComplete?.(upload);

        // Predict
        setStage("predicting");
        setMessage("Running AI analysis...");
        const prediction = await predictScan(upload.scan_id);
        onPredictionComplete?.(prediction);

        setStage("done");
        setMessage(
          `Detected: ${prediction.prediction.tumor_type.replace("_", " ")} ` +
            `(${(prediction.prediction.confidence * 100).toFixed(1)}%)`
        );
      } catch (err: unknown) {
        setStage("error");
        const msg =
          err instanceof Error ? err.message : "An unexpected error occurred";
        setMessage(msg);
        onError?.(msg);
      }
    },
    [onUploadComplete, onPredictionComplete, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "application/dicom": [".dcm"],
    },
    maxFiles: 1,
    disabled: stage === "uploading" || stage === "predicting",
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
        isDragActive
          ? "border-primary-500 bg-primary-50"
          : stage === "error"
            ? "border-red-300 bg-red-50"
            : stage === "done"
              ? "border-green-300 bg-green-50"
              : "border-slate-300 hover:border-primary-400 hover:bg-slate-50"
      }`}
    >
      <input {...getInputProps()} />
      {stage === "idle" && (
        <>
          <p className="text-slate-600 mb-1">
            {isDragActive
              ? "Drop your MRI scan here..."
              : "Drag & drop an MRI scan, or click to select"}
          </p>
          <p className="text-xs text-slate-400">PNG, JPEG, or DICOM</p>
        </>
      )}
      {(stage === "uploading" || stage === "predicting") && (
        <div className="flex items-center justify-center gap-3">
          <svg
            className="animate-spin h-5 w-5 text-primary-600"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          <span className="text-slate-600">{message}</span>
        </div>
      )}
      {stage === "done" && (
        <p className="text-green-700 font-medium">{message}</p>
      )}
      {stage === "error" && (
        <p className="text-red-600 text-sm">{message}</p>
      )}
    </div>
  );
}
