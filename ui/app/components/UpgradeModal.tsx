"use client";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api";
import { useState } from "react";

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
}

export default function UpgradeModal({ isOpen, onClose, message = "You need a full subscription to download this content." }: UpgradeModalProps) {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const isTrialing = user?.subscription_status === 'trialing';
  
  const displayMessage = isTrialing 
    ? "You are currently on a free trial. Please subscribe to the full plan to enable downloads."
    : message;

  const handleAction = async () => {
    if (isTrialing) {
      setLoading(true);
      try {
        const response = await apiClient.post<{ url: string }>("/billing/skip-trial-and-subscribe", {});
        if (response.url) {
          window.location.href = response.url;
        } else {
          // Fallback if no URL returned
          router.push("/upgrade");
        }
      } catch (error) {
        console.error("Failed to skip trial:", error);
        // Fallback to upgrade page on error
        router.push("/upgrade");
      } finally {
        setLoading(false);
      }
    } else {
      router.push("/upgrade");
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={onClose}></div>
      <div className="relative z-10 bg-[#1A1D24] border border-white/10 rounded-2xl p-8 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        
        <div className="text-center mb-8">
            <h3 className="text-xl font-bold text-white mb-2">
                {isTrialing ? "Enable Downloads" : "Upgrade Required"}
            </h3>
            <p className="text-white/60 text-sm leading-relaxed">
                {isTrialing 
                    ? "You are currently on a free trial. Please activate your subscription to enable downloads and unlock your full credit allowance."
                    : message}
            </p>
        </div>

        <div className="flex flex-col gap-3">
          <button
            onClick={handleAction}
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg1 text-black text-sm font-bold hover:shadow-lg transition-all duration-300 shadow-md disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? "Processing..." : (isTrialing ? "Activate Subscription" : "Upgrade Plan")}
          </button>
          <button
            onClick={onClose}
            className="w-full py-2 px-4 rounded-xl text-sm font-medium text-white/40 hover:text-white transition-colors"
          >
            Maybe Later
          </button>
        </div>
      </div>
    </div>
  );
}

