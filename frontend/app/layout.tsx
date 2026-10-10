import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HisabhParakh · Workspace",
  description: "Evidence-grounded voucher classification. Local workspace and service readiness.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
