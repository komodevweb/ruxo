"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Buttons from "@/app/ui/Buttons";
import Link from "next/link";
import { trackViewContent } from "@/lib/facebookTracking";

export default function LoginPage() {
  const router = useRouter();
  const { signInWithOAuth, user, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState<string | null>(null);

  // Track ViewContent when page loads
  useEffect(() => {
    if (typeof window !== 'undefined') {
      trackViewContent(`${window.location.origin}/login`);
    }
  }, []);

  // Redirect logged-in users to homepage
  useEffect(() => {
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  const handleOAuthLogin = async (provider: 'google' | 'apple' | 'microsoft') => {
    setLoading(provider);
    try {
      await signInWithOAuth(provider);
    } catch (error) {
      console.error('OAuth error:', error);
      setLoading(null);
    }
  };

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px] py-20  md:pt-[160px] pt-[110px]  min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <Link href="/" className="inline-block cursor-pointer">
              <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="Ruxo Logo" />
            </Link>
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-8 text-white">Login to Ruxo</h4>
            <div className="space-y-4">
              <button
                onClick={() => handleOAuthLogin('apple')}
                disabled={loading === 'apple'}
                className="hidden text-base font-medium leading-[120%] transition-all ease-in-out duration-500 hover:bg-gray-1800 text-black-1000 bg-white rounded-xl border border-gray-1100 flex items-center py-2.5 justify-center gap-2 w-full disabled:opacity-50"
              >
                <img src="/images/apple-logo.svg" alt="Apple" />
                {loading === 'apple' ? 'Loading...' : 'Continue with Apple'}
              </button>
              <button
                onClick={() => handleOAuthLogin('google')}
                disabled={loading === 'google'}
                className="text-base font-medium leading-[120%] transition-all ease-in-out duration-500 hover:bg-gray-1800 text-black-1000 bg-white rounded-xl border border-gray-1100 flex items-center py-2.5 justify-center gap-2 w-full disabled:opacity-50"
              >
                <img src="/images/goggle-icon.svg" alt="Google" />
                {loading === 'google' ? 'Loading...' : 'Continue with Google'}
              </button>
              <button
                onClick={() => handleOAuthLogin('microsoft')}
                disabled={loading === 'microsoft'}
                className="text-base font-medium leading-[120%] transition-all ease-in-out duration-500 hover:bg-gray-1800 text-black-1000 bg-white rounded-xl border border-gray-1100 flex items-center py-2.5 justify-center gap-2 w-full disabled:opacity-50"
              >
                <img src="/images/microsoft.svg" alt="Microsoft" />
                {loading === 'microsoft' ? 'Loading...' : 'Continue with Microsoft'}
              </button>
              <div className="flex items-center gap-4 justify-center">
                <div className="bg-white/60 opacity-50 h-px w-full"></div>
                <span className="block text-base font-medium leading-[120%] text-white/60">or</span>
                <div className="bg-white/60 opacity-50 h-px w-full"></div>
              </div>
              <Buttons
                href="/login-email"
                icon="/images/envelop.svg"
                text="Continue with Email"
              />
              <p className="text-sm font-normal leading-[120%] text-white/60">Don't have an account? <Link href="/signup" className="text-white underline">Sign Up</Link></p>
              <p className="text-xs font-normal leading-[120%] max-w-[238px] mx-auto text-white/60">By continuing, I acknowledge the <Link href="/privacy" className="underline">Privacy Policy</Link> and agree to the <Link href="/terms" className="underline"> Terms of Use.</Link> </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
