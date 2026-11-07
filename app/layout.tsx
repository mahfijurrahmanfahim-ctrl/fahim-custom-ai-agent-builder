import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FAHIM AUTOPILOT AI",
  description: "Your personal AI workspace for business, creative work and productivity."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
