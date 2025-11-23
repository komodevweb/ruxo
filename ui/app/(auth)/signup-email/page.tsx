"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import TextInput from "@/app/ui/TextInput";
import Link from "next/link";
import { trackViewContent } from "@/lib/facebookTracking";

export default function SignupEmailPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");

  // Track ViewContent when page loads
  useEffect(() => {
    if (typeof window !== 'undefined') {
      trackViewContent(`${window.location.origin}/signup-email`);
    }
  }, []);

  // Redirect logged-in users to homepage
  useEffect(() => {
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate display name
    if (!displayName || !displayName.trim()) {
      setError("Display name is required");
      return;
    }

    // Validate email
    if (!email) {
      setError("Email is required");
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address");
      return;
    }

    // Store email and display name in sessionStorage for next step
    sessionStorage.setItem("signup_email", email);
    sessionStorage.setItem("signup_display_name", displayName.trim());
    router.push("/signup-password");
  };

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px]  md:pt-[160px] pt-[110px]  py-20 min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="" />
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-8 text-white">Create stunning AI content</h4>
            <form onSubmit={handleContinue} className="mt-12 mb-8 space-y-4">
              {error && (
                <div className="text-red-500 text-sm bg-red-500/10 border border-red-500 rounded-xl p-3">
                  {error}
                </div>
              )}
              <TextInput
                type="text"
                placeholder="Display Name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
              <TextInput
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <button
                type="submit"
                className="text-base font-medium leading-[120%] text-white py-2.5 text-center bg-gray-1000 rounded-xl block border border-gray-1200 w-full transition-all ease-in-out duration-500 hover:bg-gray-1200"
              >
                Continue
              </button>
              <Link href="/signup" className="flex items-center gap-1.5 text-base font-medium text-white/[60%]">
                <img src="images/arrow-left.svg" alt="" />Back to Options
              </Link>
            </form>
            <p className="text-xs font-normal leading-[120%] max-w-[238px] mx-auto text-center text-white/60">By continuing, I acknowledge the <Link href="/privacy" className="underline">Privacy Policy</Link> and agree to the <Link href="/terms" className="underline"> Terms of Use.</Link> </p>
          </div>
        </div>
      </section>
    </div>
  );
}
