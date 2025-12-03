'use client'
import HighlightedPricingCard from '@/app/components/HighlightedPricingCard'
import PricingCard from '@/app/components/PricingCard'
import { PricingSkeleton } from '@/app/components/PricingSkeleton'
import { useState, useEffect, Suspense } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { trackInitiateCheckout, trackAddToCart } from "@/lib/facebookTracking";

interface Plan {
     id: string;
     name: string;
     display_name: string;
     amount_cents: number;
     amount_dollars: number;
     original_amount_cents?: number | null;
     original_amount_dollars?: number | null;
     interval: string;
     interval_display?: string;  // For displaying "one-time" instead of "/month" or "/year"
     credits_per_month: number;
     currency: string;
     trial_days?: number;
     trial_amount_cents?: number;
     trial_amount_dollars?: number;
     trial_credits?: number;
}


function UpgradeContent() {
     console.warn("DEBUG: Upgrade Page Component Rendered");
     const { user, loading: authLoading, checkAuth } = useAuth();
     const router = useRouter();
     const searchParams = useSearchParams();
     
     // Start with yearly by default
     const [Monthly, setMonthly] = useState<'monthly' | 'yearly'>('yearly');
     const [plans, setPlans] = useState<Plan[]>([]);
     const [loading, setLoading] = useState(true);
     const [error, setError] = useState<string | null>(null);
     const [processingPlan, setProcessingPlan] = useState<string | null>(null);
     
     // Fetch plans immediately - don't wait for auth
     useEffect(() => {
          fetchPlans();
     }, []);
     
     // Track AddToCart event when user visits the upgrade page
     useEffect(() => {
          // Track AddToCart event for Facebook Conversions API
          trackAddToCart(window.location.href).catch((error) => {
               // Silently fail - tracking should not block page functionality
               console.debug('Failed to track AddToCart on page load:', error);
          });
     }, []); // Only run once on mount
     
     
     // Refresh user data when page loads to ensure we have latest subscription info
     useEffect(() => {
          if (!authLoading && user) {
               // Force refresh user data to get latest plan info
               checkAuth();
          }
     }, []); // Only run once on mount
     
     // Auto-switch to yearly view if user has yearly plan
     useEffect(() => {
          if (user?.plan_name) {
               // Use explicit interval or fallback parsing
               let isYearly = false;
               if (user.plan_interval) {
                    isYearly = user.plan_interval === 'year';
               } else {
                    const planNameLower = user.plan_name.toLowerCase();
                    isYearly = planNameLower.includes('yearly') || 
                               planNameLower.includes('annual') || 
                               planNameLower.includes('_yearly') ||
                               planNameLower.endsWith('yearly');
               }
               
               if (isYearly && Monthly !== 'yearly') {
                    setMonthly('yearly');
               }
          }
     }, [user?.plan_name, user?.plan_interval, Monthly]);

     const fetchPlans = async () => {
          try {
               setLoading(true);
               setError(null);
               // Use fetch directly for better caching control
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/billing/plans`, {
                    method: 'GET',
                    headers: {
                         'Content-Type': 'application/json',
                    },
                    // Let browser cache this request
                    cache: 'default',
               });
               
               if (!response.ok) {
                    throw new Error(`Failed to load plans: ${response.statusText}`);
               }
               
               const data = await response.json();
               setPlans(data);
          } catch (err: any) {
               setError(err.message || 'Failed to load plans');
          } finally {
               setLoading(false);
          }
     };

     const handleSelectPlan = async (planName: string, event?: React.MouseEvent) => {
          // Log all calls to this function for debugging
          console.log('🎯 handleSelectPlan called', {
               planName,
               hasEvent: !!event,
               isTrusted: event?.isTrusted,
               eventType: event?.type,
               timestamp: new Date().toISOString()
          });
          
          // Prevent any automatic triggers - only allow actual user clicks
          // event.isTrusted is false for programmatic clicks, true for real user clicks
          if (event && !event.isTrusted) {
               console.warn('❌ InitiateCheckout blocked: Not a trusted user event');
               return;
          }
          
          // If no event provided at all, this is likely a programmatic call - block it
          if (!event) {
               console.error('❌ InitiateCheckout blocked: No event provided (likely programmatic call)');
               console.trace('Stack trace for blocked InitiateCheckout');
               return;
          }

          // Redirect to login if not authenticated
          if (!user) {
               console.log('Redirecting to login - user not authenticated');
               router.push('/login');
               return;
          }

          // Track InitiateCheckout event ONLY when user explicitly clicks to select a plan
          // Find the selected plan to get its value for tracking
          const selectedPlan = plans.find(p => p.name === planName);
          console.log('✅ User clicked Select Plan - tracking InitiateCheckout for plan:', planName, {
               value: selectedPlan?.amount_dollars,
               currency: selectedPlan?.currency,
               displayName: selectedPlan?.display_name
          });
          try {
               await trackInitiateCheckout({
                    eventSource: `button-click:${planName}`,
                    value: selectedPlan?.amount_dollars,
                    currency: selectedPlan?.currency || 'USD',
                    contentId: planName,
                    contentName: selectedPlan?.display_name || planName,
                    contentType: 'subscription',
               });
               console.log('✅ InitiateCheckout tracked successfully with value:', selectedPlan?.amount_dollars);
          } catch (error) {
               // Silently fail - tracking should not block checkout
               console.debug('Failed to track InitiateCheckout:', error);
          }

          // Set processing state immediately for fast feedback
          setProcessingPlan(planName);
          setError(null);

          try {
               // Check if API URL is configured
               if (!process.env.NEXT_PUBLIC_API_V1_URL) {
                    console.warn('NEXT_PUBLIC_API_V1_URL is not configured');
               }
               
               // Check for skip_trial query parameter OR if user already has a plan (active or trialing)
               // If user has a plan, they should pay directly (skip new trial)
               const shouldSkipTrial = 
                    (searchParams && searchParams.get('skip_trial') === 'true') || 
                    (user && user.plan_name);

               const response = await apiClient.post<{ url: string }>('/billing/create-checkout-session', {
                    plan_name: planName,
                    skip_trial: !!shouldSkipTrial
               });
               
               console.log('Checkout session response:', response);
               
               // Redirect to Stripe checkout
               if (response && response.url && typeof response.url === 'string' && response.url.startsWith('http')) {
                    console.log('Redirecting to Stripe:', response.url);
                    // Use window.location.replace to ensure redirect happens and prevent back button issues
                    // Add a small delay to ensure state updates are processed
                    setTimeout(() => {
                         window.location.replace(response.url);
                    }, 100);
               } else {
                    console.error('Invalid URL in response:', response);
                    setError('Failed to get valid checkout URL from server. Please try again.');
                    setProcessingPlan(null);
               }
          } catch (err: any) {
               console.error('Error creating checkout session:', err);
               const errorMessage = err.message || 'Failed to create checkout session';
               
               // Provide more helpful error messages
               if (errorMessage.includes('Network error') || errorMessage.includes('Failed to fetch')) {
                    setError('Unable to connect to the server. Please check if the backend is running and try again.');
               } else {
                    setError(errorMessage);
               }
               setProcessingPlan(null);
          }
     };

     const handleManagePlan = async () => {
          // Redirect to login if not authenticated
          if (!user) {
               router.push('/login');
               return;
          }

          // Set processing state
          setProcessingPlan('manage');
          setError(null);

          try {
               const response = await apiClient.post<{ url: string }>('/billing/create-portal-session');
               
               // Redirect to Stripe customer portal
               if (response && response.url) {
                    window.location.href = response.url;
               } else {
                    console.error('No URL in response:', response);
                    setError('Failed to get portal URL from server');
                    setProcessingPlan(null);
               }
          } catch (err: any) {
               console.error('Error creating portal session:', err);
               setError(err.message || 'Failed to open customer portal');
               setProcessingPlan(null);
          }
     };

     // Map plan names to display names and features
     const getPlanFeatures = (planName: string) => {
          const planMap: Record<string, { credits: number; features: string[] }> = {
               'starter': {
                    credits: 200,
                    features: [
                         '200 Credits per month',
                         '~200 images or ~20 videos',
                         '5 concurrent generations',
                         'Wan 2.5 Video & Image',
                         'Minimax Hailuo Video',
                         'Flux 1.1 Pro Ultra',
                         'Stable Diffusion 3.5',
                    ]
               },
               'pro': {
                    credits: 400,
                    features: [
                         '400 Credits per month',
                         '~400 images or ~50 videos',
                         '10 concurrent generations',
                         'Everything in Starter +',
                         'OpenAI Sora 2 🔥',
                         'Google Veo 3 & 3.1 🔥',
                         'Kling v2.5 Turbo Pro',
                         'Seedance v1 Pro',
                         'Up to 4 Images at Once',
                    ]
               },
               'creator': {
                    credits: 1000,
                    features: [
                         '1,000 Credits per month',
                         '~1,000 images or ~125 videos',
                         '20 concurrent generations',
                         'Everything in Pro +',
                         'OpenAI Sora 2 Pro 🔥',
                         'All 15+ AI Models',
                         'Up to 8 Images at Once',
                         'Creative Characters',
                    ]
               },
               'ultimate': {
                    credits: 2000,
                    features: [
                         '2,000 Credits per month',
                         '~2,000 images or ~250 videos',
                         'Unlimited concurrent',
                         'Everything in Creator +',
                         'All 15+ AI Models',
                         'Unlimited Images at Once',
                         'UGC Generator',
                         'Priority Support',
                    ]
               }
          };

          const planKey = planName.split('_')[0]; // Extract 'starter', 'pro', etc.
          return planMap[planKey] || { credits: 0, features: [] };
     };

     // Filter plans by interval
     const filteredPlans = plans.filter(plan => {
          if (Monthly === "monthly") {
               return plan.interval === "month";
          } else {
               return plan.interval === "year";
          }
     });

     // Sort plans: starter, pro, creator, ultimate
     const sortedPlans = [...filteredPlans].sort((a, b) => {
          const order = ['starter', 'pro', 'creator', 'ultimate'];
          const aIndex = order.findIndex(o => a.name.startsWith(o));
          const bIndex = order.findIndex(o => b.name.startsWith(o));
          return aIndex - bIndex;
     });

     // Get plan display name
     const getDisplayName = (planName: string) => {
          const nameMap: Record<string, string> = {
               'starter': 'Starter',
               'pro': 'Pro',
               'creator': 'Creator',
               'ultimate': 'Ultimate',
          };
          const planKey = planName.split('_')[0];
          return nameMap[planKey] || planName;
     };

     // Format price
     const formatPrice = (amountDollars: number) => {
          return new Intl.NumberFormat('en-US', {
               style: 'currency',
               currency: 'USD',
               minimumFractionDigits: 0,
               maximumFractionDigits: 0,
          }).format(amountDollars);
     };

     // Calculate monthly equivalent for yearly plans (using discounted price)
     const getMonthlyEquivalent = (plan: Plan) => {
          if (plan.interval === 'year') {
               return `$${Math.round(plan.amount_dollars / 12)}/month`;
          }
          return null;
     };
     
     // Get original price for yearly plans (before discount)
     const getOriginalPrice = (plan: Plan) => {
          if (plan.interval === 'year' && plan.original_amount_dollars) {
               return formatPrice(plan.original_amount_dollars);
          }
          return null;
     };

     // Get plan tier order (lower number = lower tier)
     const getPlanTier = (planName: string): number => {
          const tierMap: Record<string, number> = {
               'starter': 1,
               'pro': 2,
               'creator': 3,
               'ultimate': 4,
          };
          const planKey = planName.split('_')[0];
          return tierMap[planKey] || 0;
     };

     // Check if user has active subscription
     const hasActiveSubscription = user?.plan_name !== null && user?.plan_name !== undefined;
     
     // Get current plan tier if user has subscription
     // Extract plan key from display name (e.g., "Starter Monthly" -> "starter")
     const getPlanKeyFromDisplayName = (displayName: string): string => {
          const lower = displayName.toLowerCase();
          if (lower.includes('starter')) return 'starter';
          if (lower.includes('pro')) return 'pro';
          if (lower.includes('creator')) return 'creator';
          if (lower.includes('ultimate')) return 'ultimate';
          return '';
     };
     
     const currentPlanTier = hasActiveSubscription && user.plan_name 
          ? getPlanTier(getPlanKeyFromDisplayName(user.plan_name) + '_monthly') // Use dummy suffix for tier lookup
          : 0;
     
     // Get current plan interval if user has subscription
     // Use explicit plan_interval from backend if available, otherwise fallback to name parsing
     const getCurrentPlanInterval = (): 'year' | 'month' | null => {
          if (!hasActiveSubscription || !user?.plan_name) {
               return null;
          }
          
          // Debug: Log everything we know about the plan
          console.log('[Upgrade Page Debug] User Data:', {
               plan_name: user.plan_name,
               plan_interval: user.plan_interval, // This is the new field
               credits: user.credits_per_month
          });
          
          // Check explicit interval property first (new backend feature)
          if (user.plan_interval) {
               const interval = user.plan_interval === 'year' ? 'year' : 'month';
               console.log('[Upgrade Page Debug] Detected via plan_interval:', interval);
               return interval;
          }
          
          // Fallback to name parsing for backward compatibility
          const planNameLower = user.plan_name.toLowerCase();
          if (planNameLower.includes('yearly') || 
              planNameLower.includes('annual') || 
              planNameLower.includes('_yearly') ||
              planNameLower.endsWith('yearly')) {
               console.log('[Upgrade Page Debug] Detected via name parsing: year');
               return 'year';
          }
          console.log('[Upgrade Page Debug] Detected via name parsing: month');
          return 'month';
     };
     
     const currentPlanInterval = getCurrentPlanInterval();

     // Determine if plan is upgrade, downgrade, or current
     const getPlanStatus = (plan: Plan) => {
          // Check if user has an active subscription or trial
          const hasSubscription = hasActiveSubscription;
          
          // Debug logging
          console.log('[getPlanStatus] Checking plan:', {
               planName: plan.name,
               planDisplayName: plan.display_name,
               userPlanName: user?.plan_name,
               userPlanInterval: user?.plan_interval,
               hasActiveSubscription,
               hasSubscription,
               creditBalance: user?.credit_balance,
               planInterval: plan.interval
          });
          
          // If user has no plan_name, they don't have a subscription
          if (!hasSubscription || !user?.plan_name) {
               console.log('[getPlanStatus] No subscription or plan_name, returning new');
               return { type: 'new', canSelect: true };
          }
          
          const planTier = getPlanTier(plan.name);
          const planInterval = plan.interval;
          
          // Get user's plan key and interval
          const userPlanKey = getPlanKeyFromDisplayName(user.plan_name);
          const planKey = plan.name.split('_')[0];
          
          // Also check if plan display_name matches user's plan_name (more direct comparison)
          // Normalize both by lowercasing and trimming
          const normalizedUserPlan = user.plan_name.toLowerCase().trim();
          const normalizedPlanDisplay = plan.display_name.toLowerCase().trim();
          const isDisplayNameMatch = normalizedUserPlan === normalizedPlanDisplay;
          
          // Also check if plan name (internal) matches - sometimes backend might return internal name
          const normalizedPlanName = plan.name.toLowerCase().trim();
          
          // Only match if the plan name contains the specific interval we're looking for
          // or if it's an exact match
          let isPlanNameMatch = false;
          if (normalizedUserPlan === normalizedPlanName) {
               isPlanNameMatch = true;
          } else {
               // If not exact match, check if parts match AND interval matches
               const userPlanBase = normalizedUserPlan.split('_')[0].split(' ')[0]; // "starter"
               const planNameBase = normalizedPlanName.split('_')[0]; // "starter"
               
               // Check if base names match
               if (userPlanBase === planNameBase) {
                    // Check if intervals match
                    const userHasYearly = normalizedUserPlan.includes('year') || normalizedUserPlan.includes('annual');
                    const planIsYearly = normalizedPlanName.includes('year') || normalizedPlanName.includes('annual');
                    
                    // Match only if intervals are the same
                    if (userHasYearly === planIsYearly) {
                         isPlanNameMatch = true;
                    }
               }
          }
          
          console.log('[getPlanStatus] Matching details:', {
               userPlanKey,
               planKey,
               isDisplayNameMatch,
               isPlanNameMatch,
               userPlanName: user.plan_name,
               normalizedUserPlan,
               planDisplayName: plan.display_name,
               normalizedPlanDisplay,
               planName: plan.name,
               planInterval,
               currentPlanInterval
          });
          
          // If user has yearly subscription, they can only see yearly plans
          if (currentPlanInterval === 'year' && planInterval !== 'year') {
               return { type: 'incompatible', canSelect: false };
          }
          
          // If user has monthly subscription, they can see both monthly and yearly
          // (yearly would be an upgrade)
          
          // Check if this is the exact same plan (same tier AND same interval)
          // OR if display names match exactly (handles edge cases)
          // OR if plan names match (handles cases where backend returns internal name)
          const isExactMatch = isDisplayNameMatch || isPlanNameMatch || (
               userPlanKey === planKey && 
               planInterval === currentPlanInterval &&
               currentPlanInterval !== null
          );
          
          console.log('[getPlanStatus] isExactMatch:', isExactMatch);
          
          if (isExactMatch) {
               // This is the user's current plan (active subscription or trial)
               console.log('[getPlanStatus] Found exact match, returning current');
               return { type: 'current', canSelect: false };
          }
          
          // Different plans - check tier
          if (planTier > currentPlanTier) {
               // Higher tier plan - upgrade available
               return { type: 'upgrade', canSelect: true };
          } else if (planTier < currentPlanTier) {
               // Lower tier plan - downgrade (not available)
               return { type: 'downgrade', canSelect: false };
          } else {
               // Same tier but different interval
               if (userPlanKey === planKey) {
                    // Same plan type, different interval
                    if (planInterval === 'month' && currentPlanInterval === 'year') {
                         // User has yearly, viewing monthly -> incompatible
                         return { type: 'incompatible', canSelect: false };
                    }
                    if (planInterval === 'year' && currentPlanInterval === 'month') {
                         // User has monthly, viewing yearly -> upgrade
                         return { type: 'upgrade', canSelect: true };
                    }
               }
               return { type: 'same_tier', canSelect: false };
          }
     };
     return (
          <>
               <section id="upgrade" className="w-full font-inter bg-black-1100 md:pt-[160px] pt-[110px]  py-20">
                    <div className="w-full max-w-[1400px] px-5 mx-auto">
                         <div className="text-center mb-12">
                              <h2 className="md:text-[48px] text-[32px] mb-3 text-white font-medium leading-[120%] tracking-[-1px]">ALL THE BEST AI MODELS IN ONE PLACE</h2>
                              <p className="text-base font-normal leading-5 text-white/60 tracking-[-0.32px] max-w-2xl mx-auto mb-6">
                                   Access Sora, Veo, Kling, Flux and 15+ premium AI models with a single subscription.
                              </p>
                              <div className="flex flex-wrap items-center justify-center gap-2 md:gap-3 max-w-4xl mx-auto mb-6">
                                   <span className="px-3 py-1.5 rounded-full bg-gradient-to-r from-pink-500/20 to-purple-500/20 border border-pink-500/40 text-xs md:text-sm text-white font-medium">🔥 Sora 2 Pro</span>
                                   <span className="px-3 py-1.5 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/40 text-xs md:text-sm text-white font-medium">🔥 Google Veo 3.1</span>
                                   <span className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs md:text-sm text-white/80">Kling v2.5 Pro</span>
                                   <span className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs md:text-sm text-white/80">Seedance Pro</span>
                                   <span className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs md:text-sm text-white/80">Nano Banana Pro</span>
                                   <span className="px-3 py-1.5 rounded-full bg-blue2/20 border border-blue2/40 text-xs md:text-sm text-blue2 font-medium">+ New Models Weekly</span>
                              </div>

                              
                              {error && (
                                   <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                                        <p className="text-red-400 text-sm">{error}</p>
                                   </div>
                              )}
                         </div>
                         <div className="w-full flex items-center justify-center">
                              <div className="inline-flex workflow-card-border p-[1] rounded-full">
                                   <div className="inline-flex gap-6 bg-black3 rounded-full relative p-3">

                                        <div className={`${Monthly === "yearly" ? 'opacity-100' : 'opacity-0'} absolute z-0 top-0 transition rounded-full right-0 w-1/2 h-full bg-[radial-gradient(circle_at_right,rgba(59,130,246,0.2)_0%,transparent_70%)]`}></div>

                                        <button 
                                             onClick={() => setMonthly("monthly")} 
                                             disabled={currentPlanInterval === 'year'}
                                             className={`flex items-center justify-center gap-3 outline-0 relative z-10 ${currentPlanInterval === 'year' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                        >
                                             <div className="w-6 h-6 rounded-full border border-white flex items-center justify-center">
                                                  {Monthly === "monthly" && <div className="w-2.5 h-2.5 rounded-full bg-blue2 border border-blue1"></div>}
                                             </div>
                                             <span className="text-white font-medium text-sm font-inter">Monthly</span>
                                        </button>

                                        <button onClick={() => setMonthly("yearly")} className="flex cursor-pointer items-center justify-center gap-3 outline-0 relative z-10">
                                             <div className="w-6 h-6 rounded-full border border-white flex items-center justify-center">
                                                  {Monthly === "yearly" && <div className="w-2.5 h-2.5 rounded-full bg-blue2 border border-blue1"></div>}
                                             </div>
                                             <span className="text-white font-medium text-sm font-inter">Annually</span>
                                             <span className={`${Monthly === "yearly" ? 'text-white/60' : 'text-white/40'}  font-medium text-sm`}>Save 60%</span>
                                        </button>
                                   </div>
                              </div>
                         </div>

                         {loading || authLoading ? (
                              <PricingSkeleton />
                         ) : error ? (
                              <div className="text-center py-12">
                                   <p className="text-red-500">{error}</p>
                                   <button
                                        onClick={fetchPlans}
                                        className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                                   >
                                        Retry
                                   </button>
                              </div>
                         ) : sortedPlans.length === 0 ? (
                              <div className="text-center py-12">
                                   <p className="text-white/60">No plans available</p>
                              </div>
                         ) : (
                              <div className="grid mb-4 lg:grid-cols-4 md:grid-cols-2 gap-6 mt-6">
                                   {sortedPlans.map((plan, index) => {
                                        const planFeatures = getPlanFeatures(plan.name);
                                        const displayName = getDisplayName(plan.name);
                                        const monthlyEquivalent = getMonthlyEquivalent(plan);
                                        const originalPrice = getOriginalPrice(plan);
                                        const isPro = plan.name.startsWith('pro');
                                        const description = Monthly === "monthly"
                                             ? "Billed Monthly"
                                             : `Billed Annually${monthlyEquivalent ? ` • ${monthlyEquivalent}` : ''}`;

                                        // Show loading state while auth is loading
                                        const isAuthLoading = authLoading;
                                        
                                        // Get plan status only after auth has loaded, otherwise use default
                                        const planStatus = !isAuthLoading ? getPlanStatus(plan) : { type: 'new', canSelect: true };
                                        
                                        const isProcessing = processingPlan === plan.name;
                                        const isManagingPlan = processingPlan === 'manage' && planStatus.type === 'current';
                                        
                                        // Determine button text - show loading if auth is still loading
                                        let buttonText = "Select Plan";
                                        let buttonOnClick: ((e?: React.MouseEvent) => void) | undefined = undefined;
                                        
                                        // Debug logging for button text
                                        if (!isAuthLoading && user) {
                                             console.log(`[Button Text] Plan: ${plan.name}, Status: ${planStatus.type}, User Plan: ${user.plan_name}`);
                                        }
                                        
                                        if (isAuthLoading) {
                                             buttonText = "Loading...";
                                        } else if (isProcessing || isManagingPlan) {
                                             buttonText = "Processing...";
                                        } else if (planStatus.type === 'upgrade') {
                                             buttonText = "Upgrade";
                                             buttonOnClick = (e?: React.MouseEvent) => handleSelectPlan(plan.name, e);
                                        } else if (planStatus.type === 'current') {
                                             // For trial users, show "Current Plan" instead of "Manage Subscription"
                                             // since there's nothing to manage in Stripe yet
                                             if (user?.subscription_status === 'trialing') {
                                                  buttonText = "Current Plan";
                                                  // No onClick - button is just informational
                                             } else {
                                             buttonText = "Manage Subscription";
                                             buttonOnClick = handleManagePlan;
                                             }
                                        } else if (planStatus.type === 'downgrade' || planStatus.type === 'incompatible') {
                                             // Show "Not Available" for any downgrade or incompatible plan
                                             buttonText = "Not Available";
                                        } else if (planStatus.type === 'new') {
                                             buttonText = "Start Free Trial";
                                             buttonOnClick = (e?: React.MouseEvent) => handleSelectPlan(plan.name, e);
                                        } else if (planStatus.canSelect) {
                                             buttonOnClick = (e?: React.MouseEvent) => handleSelectPlan(plan.name, e);
                                        }
                                        
                                        // Dim any card that shows "Not Available"
                                        const shouldDim = isAuthLoading ? false : (buttonText === "Not Available");
                                        
                                        // Determine duration display - handle one-time payments
                                        let durationDisplay = Monthly === "monthly" ? "/month" : "/year";
                                        if (plan.interval === "one_time" || plan.interval_display === "one-time") {
                                             durationDisplay = " one-time";
                                        }
                                        
                                        const cardProps = {
                                             plan: displayName,
                                             price: formatPrice(plan.amount_dollars),
                                             originalPrice: originalPrice,
                                             duration: durationDisplay,
                                             description: description,
                                             planInlude: `${displayName} Plan includes`,
                                             buttonText: buttonText,
                                             buttonDisabled: isAuthLoading || isProcessing || isManagingPlan || (!!processingPlan && processingPlan !== plan.name && processingPlan !== 'manage'),
                                             features: planFeatures.features.map(f => ({ text: f })),
                                             onClick: buttonOnClick,
                                             isDimmed: shouldDim,
                                        };

                                        return isPro ? (
                                             <HighlightedPricingCard key={plan.id} {...cardProps} />
                                        ) : (
                                             <PricingCard key={plan.id} {...cardProps} />
                                        );
                                   })}
                              </div>
                         )}
                         
                         {/* Reviews Section */}
                         <div className="w-full max-w-6xl mx-auto mt-20 pb-10 border-t border-white/5 pt-16">
                              <div className="flex flex-col items-center mb-12">
                                   <div className="flex items-center gap-2 mb-3 bg-white/5 px-4 py-2 rounded-full border border-white/10">
                                        <div className="flex">
                                             {[...Array(5)].map((_, i) => (
                                                  <svg key={i} className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                                                       <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                  </svg>
                                             ))}
                                        </div>
                                        <span className="text-white font-semibold text-sm">4.9/5</span>
                                        <span className="text-white/40 text-sm border-l border-white/20 pl-2">Trusted by 2,400+ creators</span>
                                   </div>
                                   <h3 className="text-2xl md:text-3xl font-medium text-white text-center mb-2">Loved by creators</h3>
                                   <p className="text-white/50 text-center max-w-lg">See why thousands of creators switched to Ruxo for their AI video generation.</p>
                              </div>
                              
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 px-4">
                                   {/* Review 1 */}
                                   <div className="bg-gradient-to-b from-white/[0.07] to-white/[0.02] border border-white/10 rounded-2xl p-6 backdrop-blur-sm hover:border-white/20 transition-all duration-300">
                                        <div className="flex items-center gap-1 mb-4">
                                             {[...Array(5)].map((_, i) => (
                                                  <svg key={i} className="w-4 h-4 text-yellow-400/80" fill="currentColor" viewBox="0 0 20 20">
                                                       <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                  </svg>
                                             ))}
                                        </div>
                                        <p className="text-white/80 text-sm leading-relaxed mb-6 min-h-[60px]">"Finally one place for all AI video tools. Saved me hundreds on subscriptions. The workflow is seamless."</p>
                                        <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                                             <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-sm shadow-inner">MT</div>
                                             <div>
                                                  <p className="text-white font-medium text-sm">Marcus T.</p>
                                                  <p className="text-white/40 text-xs">Content Creator</p>
                                             </div>
                                        </div>
                                   </div>

                                   {/* Review 2 */}
                                   <div className="bg-gradient-to-b from-white/[0.07] to-white/[0.02] border border-white/10 rounded-2xl p-6 backdrop-blur-sm hover:border-white/20 transition-all duration-300">
                                        <div className="flex items-center gap-1 mb-4">
                                             {[...Array(5)].map((_, i) => (
                                                  <svg key={i} className="w-4 h-4 text-yellow-400/80" fill="currentColor" viewBox="0 0 20 20">
                                                       <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                  </svg>
                                             ))}
                                        </div>
                                        <p className="text-white/80 text-sm leading-relaxed mb-6 min-h-[60px]">"The Veo and Sora quality is incredible. It's been the best investment for my agency's production pipeline."</p>
                                        <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                                             <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-sm shadow-inner">SK</div>
                                             <div>
                                                  <p className="text-white font-medium text-sm">Sarah K.</p>
                                                  <p className="text-white/40 text-xs">Marketing Agency</p>
                                             </div>
                                        </div>
                                   </div>

                                   {/* Review 3 */}
                                   <div className="bg-gradient-to-b from-white/[0.07] to-white/[0.02] border border-white/10 rounded-2xl p-6 backdrop-blur-sm hover:border-white/20 transition-all duration-300">
                                        <div className="flex items-center gap-1 mb-4">
                                             {[...Array(5)].map((_, i) => (
                                                  <svg key={i} className="w-4 h-4 text-yellow-400/80" fill="currentColor" viewBox="0 0 20 20">
                                                       <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                  </svg>
                                             ))}
                                        </div>
                                        <p className="text-white/80 text-sm leading-relaxed mb-6 min-h-[60px]">"New models added weekly - I don't have to worry about missing out on the latest AI tech anymore."</p>
                                        <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                                             <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500/20 to-pink-500/20 border border-white/10 flex items-center justify-center text-white font-bold text-sm shadow-inner">JR</div>
                                             <div>
                                                  <p className="text-white font-medium text-sm">James R.</p>
                                                  <p className="text-white/40 text-xs">Indie Filmmaker</p>
                                             </div>
                                        </div>
                                   </div>
                              </div>
                         </div>
                    </div>
               </section>
          </>
     )
}

export default function UpgradePage() {
     return (
          <Suspense fallback={<PricingSkeleton />}>
               <UpgradeContent />
          </Suspense>
     );
}
