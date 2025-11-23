import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign Up - Ruxo - Create Your Free Account",
  description: "Create your free Ruxo account to start generating AI photos and videos. Sign up with email, Google, Apple, or Microsoft.",
  keywords: "sign up, create account, register, Ruxo signup, free account",
  openGraph: {
    title: "Sign Up - Ruxo",
    description: "Create your free Ruxo account to start generating AI photos and videos.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Sign Up - Ruxo",
    description: "Create your free Ruxo account.",
  },
};

export default function SignupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

