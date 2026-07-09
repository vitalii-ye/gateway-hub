import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gateway Hub",
  description: "Control panel for GatewayHub event ingestion gateway",
};

export const viewport: Viewport = {
  themeColor: "#0D0F11",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-void text-text font-body antialiased">
        {children}
      </body>
    </html>
  );
}