"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";

export default function BillingSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkAuth } = useAuth();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    const upgraded = searchParams.get("upgraded");
    
    // Refresh user data to get updated subscription info
    checkAuth().finally(() => {
      setLoading(false);
    });
    
    // Auto-redirect after a delay (without query params)
    const timer = setTimeout(() => {
      router.push('/settings');
    }, upgraded === 'true' ? 2000 : 3000);
    
    return () => clearTimeout(timer);
  }, [searchParams, checkAuth, router]);

  if (loading) {
    return (
      <div className="font-inter bg-black-1100 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-white/60">Processing your subscription...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="font-inter bg-black-1100 min-h-screen flex items-center justify-center">
      <div className="max-w-[500px] w-full px-5 mx-auto text-center">
        <div className="mb-8">
          <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-medium text-white mb-2">
            {searchParams.get("upgraded") === "true" ? "Upgrade Successful!" : "Payment Successful!"}
          </h1>
          <p className="text-white/60 mb-8">
            {searchParams.get("upgraded") === "true" 
              ? "Your plan has been upgraded and credits have been added to your account."
              : "Your subscription has been activated. You can now start using your credits."}
          </p>
        </div>
        <div className="flex gap-4 justify-center">
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/settings"
            className="px-6 py-3 bg-gray-800 text-white rounded-xl font-medium hover:bg-gray-700 transition-colors"
          >
            Manage Subscription
          </Link>
        </div>
      </div>
    </div>
  );
}

