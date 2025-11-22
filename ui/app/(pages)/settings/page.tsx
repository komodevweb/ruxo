"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api";
import TextInput from "@/app/ui/TextInput";
import Link from "next/link";
import { SettingsSkeleton } from '@/app/components/SettingsSkeleton';

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, signOut, loading: authLoading, checkAuth } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [isEditingDisplayName, setIsEditingDisplayName] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Clean up session_id from URL if present
  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      // Remove session_id from URL without reloading
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }

    if (user) {
      setDisplayName(user.display_name || "");
    }
  }, [user, authLoading, router]);

  const handleUpdateDisplayName = async () => {
    if (!displayName.trim()) {
      setError("Display name is required");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const updatedUser = await apiClient.put("/auth/me", {
        display_name: displayName.trim(),
      });
      
      // Refresh user data in auth context
      await checkAuth();
      
      setIsEditingDisplayName(false);
    } catch (error: any) {
      setError(error.message || "Failed to update display name");
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
  };

  if (authLoading) {
    return <SettingsSkeleton />;
  }

  if (!user) {
    return null;
  }

  const creditUsage = user.credit_balance || 0;
  const creditLimit = user.credits_per_month || null; // Credits from plan
  const creditPercentage = creditLimit 
    ? Math.min((creditUsage / creditLimit) * 100, 100) 
    : 0;

  return (
    <div className="font-inter">
      <section className="py-12 md:pt-[160px] pt-[110px] min-h-[calc(100vh_-_56px)] bg-black-1100 flex items-center justify-center">
        <div className='max-w-[740px] w-full px-5 mx-auto'>
          {/* Profile Header */}
          <div className='icon-bg p-6 mb-6 shadow-4xl rounded-2xl flex items-center gap-6'>
            <img 
              src={user.avatar_url || "/images/avatar.svg"} 
              alt={user.display_name || "User"} 
              className="w-16 h-16 rounded-full object-cover"
            />
            <div>
              <h4 className='text-2xl font-medium leading-[120%] text-white mb-2'>
                {user.display_name || "User"}
              </h4>
              <p className='text-sm font-medium leading-[120%] text-white/[60%]'>{user.email}</p>
            </div>
          </div>

          {/* Plan Details */}
          <div className='icon-bg p-6 mb-6 shadow-4xl space-y-6 rounded-2xl'>
            <h6 className='text-base font-bold text-white leading-[120%]'>Plan Details</h6>
            <div>
              <div className='flex items-center justify-between'>
                <span className='block text-base font-medium leading-[120%] text-white/[60%]'>Credit Usage</span>
                <span className='block text-sm font-medium leading-[120%] text-white/[60%]'>
                  {creditUsage}{creditLimit ? `/${creditLimit}` : ''}
                </span>
              </div>
              <div className='h-1.5 rounded-[17px] mt-4 overflow-hidden bg-gray-1200/[50%]'>
                <div 
                  className='rounded-[17px] h-1.5 progress-bg'
                  style={{ width: `${creditPercentage}%` }}
                ></div>
              </div>
              <div className='flex items-center justify-between mt-8 mb-2'>
                <span className='block text-base font-medium leading-[120%] text-white/[60%]'>Current Plan</span>
                <Link href="/pricing" className='block text-xs font-normal underline leading-[120%] text-white/[60%]'>
                  {user.plan_name ? "Manage" : "Subscribe"}
                </Link>
              </div>
              <h6 className='text-base font-medium leading-[120%] text-white'>
                {user.plan_name || "No Plan"}
              </h6>
              {!user.plan_name && (
                <div className='mt-4 rounded-lg border border-blue-1100 bg-[url(/images/card-bg.png)] bg-cover bg-no-repeat overflow-hidden p-[14px] flex items-center justify-between'>
                  <div>
                    <h6 className='text-xs font-medium leading-[120%] text-blue-1100 mb-1'>Upgrade Your Plan</h6>
                    <p className='text-[10px] font-medium leading-[120%] text-white/60'>Do more with the Ultimate or Creator Plan</p>
                  </div>
                  <Link 
                    href="/pricing" 
                    className='text-[10px] font-medium leading-[120%] text-white inline-block py-[9px] px-2 transition-all ease-in-out duration-500 hover:bg-gray-1200 bg-gray-1100/30 rounded-lg backdrop-blur-[4px]'
                  >
                    Upgrade
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Account Details */}
          <div className='icon-bg p-6 mb-6 shadow-4xl space-y-6 rounded-2xl'>
            <h6 className='text-base font-bold text-white leading-[120%]'>Account Details</h6>
            <div className='space-y-8'>
              {/* Display Name */}
              <div>
                <div className='flex items-center mb-2 justify-between'>
                  <span className='block text-base font-medium leading-[120%] text-white/[60%]'>Display Name</span>
                  {!isEditingDisplayName ? (
                    <button
                      onClick={() => setIsEditingDisplayName(true)}
                      className='block text-xs font-normal underline leading-[120%] text-white/[60%] hover:text-white cursor-pointer'
                    >
                      Edit
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setIsEditingDisplayName(false);
                          setDisplayName(user.display_name || "");
                          setError("");
                        }}
                        className='block text-xs font-normal underline leading-[120%] text-white/[60%] hover:text-white cursor-pointer'
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateDisplayName}
                        disabled={saving || !displayName.trim()}
                        className="text-xs font-medium leading-[120%] text-white py-1.5 px-3 bg-gray-1000 rounded-lg border border-gray-1200 transition-all ease-in-out duration-500 hover:bg-gray-1200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {saving ? "Saving..." : "Save"}
                      </button>
                    </div>
                  )}
                </div>
                {isEditingDisplayName ? (
                  <div className="space-y-2">
                    <TextInput
                      type="text"
                      placeholder="Display Name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      required
                    />
                    {error && (
                      <div className="text-red-500 text-sm bg-red-500/10 border border-red-500 rounded-xl p-2">
                        {error}
                      </div>
                    )}
                  </div>
                ) : (
                  <h6 className='text-base font-medium text-white leading-[120%]'>
                    {user.display_name || "Not set"}
                  </h6>
                )}
              </div>

              {/* Email */}
              <div>
                <div className='flex items-center mb-2 justify-between'>
                  <span className='block text-base font-medium leading-[120%] text-white/[60%]'>Email</span>
                  <span className='block text-xs font-normal leading-[120%] text-white/[40%]'>Cannot be changed</span>
                </div>
                <h6 className='text-base font-medium text-white leading-[120%]'>{user.email}</h6>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className='icon-bg p-6 shadow-4xl flex items-center justify-between rounded-2xl'>
            <button
              onClick={handleSignOut}
              className='text-base font-medium flex items-center gap-2 leading-[120%] text-white/[60%] hover:text-white transition-colors bg-transparent cursor-pointer'
            >
              <img src="/images/SignOut.svg" alt="" />Log Out
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
