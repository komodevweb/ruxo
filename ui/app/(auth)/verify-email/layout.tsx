import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Verify Email - Ruxo - Confirm Your Email Address",
  description: "Verify your email address to complete your Ruxo account setup and start using AI creation tools.",
  keywords: "verify email, email verification, confirm email, Ruxo verification",
  openGraph: {
    title: "Verify Email - Ruxo",
    description: "Verify your email address to complete your Ruxo account setup.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Verify Email - Ruxo",
    description: "Confirm your email address to complete your account setup.",
  },
};

export default function VerifyEmailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

