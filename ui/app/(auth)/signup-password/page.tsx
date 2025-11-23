"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import TextInput from "@/app/ui/TextInput";
import Link from "next/link";
import { trackViewContent } from "@/lib/facebookTracking";

export default function SignupPasswordPage() {
  const router = useRouter();
  const { signUp, user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Track ViewContent when page loads
  useEffect(() => {
    if (typeof window !== 'undefined') {
      trackViewContent(`${window.location.origin}/signup-password`);
    }
  }, []);

  // Redirect logged-in users to homepage
  useEffect(() => {
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    // Get email and display name from previous step
    const storedEmail = sessionStorage.getItem("signup_email");
    const storedDisplayName = sessionStorage.getItem("signup_display_name");
    
    if (storedEmail) {
      setEmail(storedEmail);
      if (storedDisplayName) {
        setDisplayName(storedDisplayName);
      }
    } else {
      router.push("/signup-email");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!displayName || !displayName.trim()) {
      setError("Display name is required");
      setLoading(false);
      return;
    }

    const result = await signUp(email, password, displayName.trim());

    if (result.error) {
      setError(result.error);
      setLoading(false);
    } else {
      // Clear stored data
      sessionStorage.removeItem("signup_email");
      sessionStorage.removeItem("signup_display_name");
      // If message exists, it means email verification is needed
      if (result.message) {
        router.push("/verify-email");
      } else {
        // User is logged in, go to home page
        router.push("/");
      }
    }
  };

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px] py-20  md:pt-[160px] pt-[110px]  min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="" />
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-8 text-white">Create stunning AI content</h4>
            <form onSubmit={handleSubmit} className="mt-12 mb-8 space-y-4">
              {error && (
                <div className="text-red-500 text-sm bg-red-500/10 border border-red-500 rounded-xl p-3">
                  {error}
                </div>
              )}
              {displayName && (
                <input
                  type="text"
                  disabled
                  value={displayName}
                  placeholder="Display Name"
                  className="text-base font-normal leading-[120%] text-white/60 w-full px-4 h-12 bg-black-1000 rounded-xl border border-gray-1000 cursor-not-allowed"
                />
              )}
              <input
                type="email"
                disabled
                value={email}
                className="text-base font-normal leading-[120%] text-white/60 w-full px-4 h-12 bg-black-1000 rounded-xl border border-gray-1000 cursor-not-allowed"
              />
              <TextInput
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
              <button
                type="submit"
                disabled={loading}
                className="text-base font-medium leading-[120%] text-white py-2.5 text-center bg-gray-1000 rounded-xl block border border-gray-1200 w-full transition-all ease-in-out duration-500 hover:bg-gray-1200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Creating Account..." : "Create Account"}
              </button>
              <Link href="/signup-email" className="flex items-center gap-1.5 text-base font-medium text-white/[60%]">
                <img src="images/arrow-left.svg" alt="" />Change Email
              </Link>
            </form>
            <p className="text-xs font-normal leading-[120%] max-w-[238px] mx-auto text-center text-white/60">By continuing, I acknowledge the <Link href="/privacy" className="underline">Privacy Policy</Link> and agree to the <Link href="/terms" className="underline"> Terms of Use.</Link> </p>
          </div>
        </div>
      </section>
    </div>
  );
}
