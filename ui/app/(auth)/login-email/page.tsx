"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import TextInput from "@/app/ui/TextInput";
import Link from "next/link";
import { trackViewContent } from "@/lib/facebookTracking";

export default function LoginEmailPage() {
  const router = useRouter();
  const { signIn, user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Track ViewContent when page loads
  useEffect(() => {
    if (typeof window !== 'undefined') {
      trackViewContent(`${window.location.origin}/login-email`);
    }
  }, []);

  // Redirect logged-in users to homepage
  useEffect(() => {
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error } = await signIn(email, password);

    if (error) {
      setError(error);
      setLoading(false);
    } else {
      router.push("/");
    }
  };

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px] md:pt-[160px] pt-[110px]  py-20 min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="" />
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-8 text-white">Login to Ruxo</h4>
            <form onSubmit={handleSubmit} className="mt-12 mb-8 space-y-4">
              {error && (
                <div className="text-red-500 text-sm bg-red-500/10 border border-red-500 rounded-xl p-3">
                  {error}
                </div>
              )}
              <TextInput
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <TextInput
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="submit"
                disabled={loading}
                className="text-base font-medium leading-[120%] text-white py-2.5 text-center bg-gray-1000 rounded-xl block border border-gray-1200 w-full transition-all ease-in-out duration-500 hover:bg-gray-1200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Logging in..." : "Log In"}
              </button>
              <div className="flex items-center justify-between">
                <Link href="/login" className="flex items-center gap-1.5 text-base font-medium text-white/[60%]">
                  <img src="images/arrow-left.svg" alt="" />Back to Options
                </Link>
                <Link href="/forgot-password" className="flex items-center gap-2 text-base font-normal text-gray-1200">
                  Forgot Password
                </Link>
              </div>
            </form>
            <p className="text-xs font-normal leading-[120%] max-w-[238px] mx-auto text-center text-white/60">By continuing, I acknowledge the <Link href="/privacy" className="underline">Privacy Policy</Link> and agree to the <Link href="/terms" className="underline"> Terms of Use.</Link> </p>
          </div>
        </div>
      </section>
    </div>
  );
}
