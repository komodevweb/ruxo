"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import TextInput from "@/app/ui/TextInput";
import Link from "next/link";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { resetPassword, user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirect logged-in users to homepage
  useEffect(() => {
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  // Validate email format
  const isValidEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Get email and code from URL params if coming from email link
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const emailParam = urlParams.get("email");
    const codeParam = urlParams.get("code");
    
    if (emailParam) {
      setEmail(emailParam);
    }
    if (codeParam) {
      setCode(codeParam);
    }
  }, []);

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Call backend to reset password with code
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/reset-password/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email, 
          code, 
          new_password: newPassword 
        }),
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to reset password. Please check your code and try again.');
        setLoading(false);
        return;
      }

      // Success - redirect to login
      router.push("/login");
    } catch (error: any) {
      setError(error.message || 'Failed to reset password');
      setLoading(false);
    }
  };

  const handleSendCode = async () => {
    if (!email) {
      setError("Please enter your email first");
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setLoading(true);
    setError("");

    const { error } = await resetPassword(email);

    if (error) {
      setError(error);
    } else {
      setError("");
      // Show success message
      alert("Reset code sent to your email. Please check your inbox.");
    }
    setLoading(false);
  };

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px] py-20 md:pt-[160px] pt-[110px] min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="" />
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-2 text-white">Reset Your Password</h4>
            <div className="w-12 h-0.5 bg-blue-1100 mx-auto mb-8"></div>
            <form onSubmit={handleResetPassword} className="mt-12 mb-8 space-y-4">
              {error && (
                <div className="text-red-500 text-sm bg-red-500/10 border border-red-500 rounded-xl p-3">
                  {error}
                </div>
              )}
              <TextInput
                type="email"
                placeholder="john@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              {isValidEmail(email) && (
                <div className="flex items-center gap-2 animate-fade-in">
                  <TextInput
                    type="text"
                    placeholder="Code"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    required
                    className="flex-1"
                  />
                  <button
                    type="button"
                    onClick={handleSendCode}
                    disabled={loading || !isValidEmail(email)}
                    className="text-sm font-medium leading-[120%] text-white py-2.5 px-4 bg-gray-1000 rounded-xl border border-gray-1200 transition-all ease-in-out duration-500 hover:bg-gray-1200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    {loading ? "Sending..." : "Send Code"}
                  </button>
                </div>
              )}
              {code && (
                <div className="animate-fade-in">
                  <TextInput
                    type="password"
                    placeholder="New Password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="text-base font-medium leading-[120%] text-white py-2.5 text-center bg-gray-1000 rounded-xl block border border-gray-1200 w-full transition-all ease-in-out duration-500 hover:bg-gray-1200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Changing Password..." : "Change Password"}
              </button>
              <div className="flex items-center justify-between">
                <Link href="/login-email" className="flex items-center gap-1.5 text-base font-medium text-white/[60%] hover:text-white transition-colors">
                  <img src="images/arrow-left.svg" alt="" />Back
                </Link>
                <button
                  type="button"
                  onClick={handleSendCode}
                  disabled={loading || !email}
                  className="flex items-center gap-1.5 text-base font-medium text-white/[60%] hover:text-white transition-colors bg-transparent disabled:opacity-50"
                >
                  <svg className="w-4 h-4 rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Resend Code
                </button>
              </div>
            </form>
            <p className="text-xs font-normal leading-[120%] max-w-[238px] mx-auto text-center text-white/60">By continuing, I acknowledge the <Link href="/privacy" className="underline">Privacy Policy</Link> and agree to the <Link href="/terms" className="underline"> Terms of Use.</Link> </p>
          </div>
        </div>
      </section>
    </div>
  );
}
