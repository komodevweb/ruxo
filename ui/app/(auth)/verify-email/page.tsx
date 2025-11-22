"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";

export default function VerifyEmailPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    // If user is logged in (verified or not), redirect to homepage
    if (!authLoading && user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  return (
    <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
      <section className="md:py-[88px] py-20  md:pt-[160px] pt-[110px]  min-h-screen flex items-center justify-center">
        <div className="max-w-[1320px] w-full px-5 mx-auto">
          <div className="max-w-[420px] w-full text-center mx-auto">
            <img src="images/logo-2.png" className="inline-block rounded-[22px] shadow-6xl" alt="" />
            <h4 className="text-[32px] font-medium leading-[120%] tracking-[-1px] mt-6 mb-8 text-white">Verify Your Email</h4>
            <div className="space-y-4">
              <p className="text-base text-white/60">
                We've sent a verification email to your inbox. Please check your email and click the verification link to activate your account.
              </p>
              <p className="text-sm text-white/60">
                Didn't receive the email? Check your spam folder or{" "}
                <Link href="/signup" className="text-white underline">try signing up again</Link>.
              </p>
              <Link
                href="/login"
                className="text-base font-medium leading-[120%] text-white py-2.5 text-center bg-gray-1000 rounded-xl block border border-gray-1200 w-full transition-all ease-in-out duration-500 hover:bg-gray-1200"
              >
                Back to Login
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
