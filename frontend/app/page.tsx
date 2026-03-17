import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Brain Tumor AI Diagnostic Platform
        </h1>
        <p className="text-lg text-slate-600 mb-8">
          Upload MRI scans for AI-powered tumor detection, Grad-CAM
          explainability overlays, and structured radiology reports.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/dashboard"
            className="bg-primary-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-primary-700 transition-colors"
          >
            Open Dashboard
          </Link>
          <Link
            href="/upload"
            className="border border-primary-600 text-primary-600 px-6 py-3 rounded-lg font-medium hover:bg-primary-50 transition-colors"
          >
            Upload Scan
          </Link>
        </div>
      </div>
    </main>
  );
}
