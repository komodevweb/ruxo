import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Upgrade Your Plan - Ruxo - Choose the Perfect AI Creation Plan",
  description: "Choose the perfect plan for your AI creation needs. Upgrade to get more credits, access to premium models, and advanced features.",
  keywords: "ruxo pricing, AI creation plans, upgrade plan, subscription plans, AI video plans, AI image plans",
  openGraph: {
    title: "Upgrade Your Plan - Ruxo",
    description: "Choose the perfect plan for your AI creation needs. Upgrade to get more credits and premium features.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Upgrade Your Plan - Ruxo",
    description: "Choose the perfect plan for your AI creation needs.",
  },
};

export default function UpgradeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

