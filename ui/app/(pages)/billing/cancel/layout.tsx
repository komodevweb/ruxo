import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Payment Cancelled - Ruxo - Subscription Not Completed",
  description: "Your payment was cancelled. You can try again or choose a different plan to upgrade your Ruxo account.",
  keywords: "payment cancelled, subscription cancelled, billing cancelled, Ruxo payment",
  openGraph: {
    title: "Payment Cancelled - Ruxo",
    description: "Your payment was cancelled. You can try again or choose a different plan.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Payment Cancelled - Ruxo",
    description: "Your payment was cancelled.",
  },
};

export default function BillingCancelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

