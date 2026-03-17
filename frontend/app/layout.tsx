import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brain Tumor AI Diagnostic Platform",
  description:
    "AI-powered brain tumor detection with Grad-CAM explainability and structured radiology reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
