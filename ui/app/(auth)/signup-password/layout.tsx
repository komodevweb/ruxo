import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Password - Ruxo - Complete Your Sign Up",
  description: "Create a secure password to complete your Ruxo account registration.",
  keywords: "create password, signup password, account setup, Ruxo signup",
  openGraph: {
    title: "Create Password - Ruxo",
    description: "Create a secure password to complete your Ruxo account registration.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Create Password - Ruxo",
    description: "Complete your Ruxo account registration.",
  },
};

export default function SignupPasswordLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

