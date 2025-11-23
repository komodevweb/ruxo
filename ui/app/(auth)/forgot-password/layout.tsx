import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Forgot Password - Ruxo - Reset Your Password",
  description: "Reset your Ruxo account password. Enter your email to receive password reset instructions.",
  keywords: "forgot password, reset password, password recovery, Ruxo password",
  openGraph: {
    title: "Forgot Password - Ruxo",
    description: "Reset your Ruxo account password. Enter your email to receive password reset instructions.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Forgot Password - Ruxo",
    description: "Reset your Ruxo account password.",
  },
};

export default function ForgotPasswordLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

