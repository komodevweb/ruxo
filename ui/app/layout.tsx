import type { Metadata } from "next";
import "./globals.css";
import Header from "./components/Header";
import { AuthProvider } from "@/contexts/AuthContext";

export const metadata: Metadata = {
  title: "Ruxo - AI Photo & Video Generation",
  description: "Create stunning AI-generated photos and videos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-black-1100 font-inter">
        <AuthProvider>
          <Header></Header>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
