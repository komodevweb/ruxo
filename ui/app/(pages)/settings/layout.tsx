import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Account Settings - Ruxo - Manage Your Profile & Subscription",
  description: "Manage your Ruxo account settings, profile information, subscription plan, and credit usage.",
  keywords: "account settings, profile settings, subscription management, Ruxo settings",
  openGraph: {
    title: "Account Settings - Ruxo",
    description: "Manage your Ruxo account settings, profile information, and subscription plan.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Account Settings - Ruxo",
    description: "Manage your Ruxo account settings and profile.",
  },
};

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

