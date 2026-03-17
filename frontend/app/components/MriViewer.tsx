"use client";

import { useState } from "react";
import Image from "next/image";

interface MriViewerProps {
  scanUrl: string;
  gradcamUrl?: string | null;
  alt?: string;
}

export default function MriViewer({
  scanUrl,
  gradcamUrl,
  alt = "MRI Scan",
}: MriViewerProps) {
  const [showOverlay, setShowOverlay] = useState(false);
  const displayUrl = showOverlay && gradcamUrl ? gradcamUrl : scanUrl;

  return (
    <div className="relative bg-black rounded-lg overflow-hidden">
      <div className="relative aspect-square w-full max-w-lg mx-auto">
        <Image
          src={displayUrl}
          alt={alt}
          fill
          className="object-contain"
          unoptimized
        />
      </div>
      {gradcamUrl && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
          <button
            onClick={() => setShowOverlay(!showOverlay)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              showOverlay
                ? "bg-red-500 text-white"
                : "bg-white/90 text-slate-700 hover:bg-white"
            }`}
          >
            {showOverlay ? "Hide Grad-CAM" : "Show Grad-CAM"}
          </button>
        </div>
      )}
    </div>
  );
}
