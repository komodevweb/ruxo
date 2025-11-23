import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login - Ruxo - Sign In to Your Account",
  description: "Sign in to your Ruxo account to access AI photo and video generation tools. Login with email, Google, Apple, or Microsoft.",
  keywords: "login, sign in, Ruxo login, account login",
  openGraph: {
    title: "Login - Ruxo",
    description: "Sign in to your Ruxo account to access AI photo and video generation tools.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Login - Ruxo",
    description: "Sign in to your Ruxo account.",
  },
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

