import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Payment Successful - Ruxo - Subscription Activated",
  description: "Your Ruxo subscription has been successfully activated. Start creating amazing AI content with your new plan.",
  keywords: "payment success, subscription activated, billing success, Ruxo payment",
  openGraph: {
    title: "Payment Successful - Ruxo",
    description: "Your Ruxo subscription has been successfully activated.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Payment Successful - Ruxo",
    description: "Your subscription has been activated.",
  },
};

export default function BillingSuccessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

