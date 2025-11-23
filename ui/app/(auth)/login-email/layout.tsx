import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login with Email - Ruxo - Sign In to Your Account",
  description: "Sign in to your Ruxo account using your email and password.",
  keywords: "login, email login, sign in, Ruxo login",
  openGraph: {
    title: "Login with Email - Ruxo",
    description: "Sign in to your Ruxo account using your email and password.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Login with Email - Ruxo",
    description: "Sign in to your Ruxo account.",
  },
};

export default function LoginEmailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

