"use client";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="font-inter bg-black-1100 min-h-screen flex items-center justify-center">
      <div className="max-w-[500px] w-full px-5 mx-auto text-center">
        <div className="mb-8">
          <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-medium text-white mb-2">
            Payment Cancelled
          </h1>
          <p className="text-white/60 mb-8">
            Your payment was cancelled. No charges were made to your account.
          </p>
        </div>
        <div className="flex gap-4 justify-center">
          <Link
            href="/upgrade"
            className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
          >
            Back to Upgrade
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-gray-800 text-white rounded-xl font-medium hover:bg-gray-700 transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

