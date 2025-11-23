import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign Up with Email - Ruxo - Create Your Free Account",
  description: "Create your free Ruxo account using your email address.",
  keywords: "sign up, email signup, create account, register, Ruxo signup",
  openGraph: {
    title: "Sign Up with Email - Ruxo",
    description: "Create your free Ruxo account using your email address.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Sign Up with Email - Ruxo",
    description: "Create your free Ruxo account.",
  },
};

export default function SignupEmailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

