'use client'
import HighlightedPricingCard from '@/app/components/HighlightedPricingCard'
import PricingCard from '@/app/components/PricingCard'
import { PricingSkeleton } from '@/app/components/PricingSkeleton'
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
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
     credits_per_month: number;
     currency: string;
}

function page() {
     console.warn("DEBUG: Upgrade Page Component Rendered");
     const { user, loading: authLoading, checkAuth } = useAuth();
     const router = useRouter();
     
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
               
               const response = await apiClient.post<{ url: string }>('/billing/create-checkout-session', {
                    plan_name: planName,
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
                         'Generate up to 200 images',
                         'Generate up to 20 videos',
                         '5 concurrent generations',
                         'Image & Video upscaling',
                         'Video Models: Wan 2.2',
                         'Standard Image Quality',
                    ]
               },
               'pro': {
                    credits: 400,
                    features: [
                         '400 Credits per month',
                         'Generate up to 400 images',
                         'Generate up to 40 videos',
                         '10 concurrent generations',
                         'Image & Video upscaling',
                         'Video Models: Wan 2.2',
                         'Standard Image Quality',
                         'Up to 4 Images at Once',
                         'Google Veo3',
                    ]
               },
               'creator': {
                    credits: 1000,
                    features: [
                         '1,000 Credits per month',
                         'Generate up to 1,000 images',
                         'Generate up to 100 videos',
                         '20 concurrent generations',
                         'Image & Video upscaling',
                         'Video Models: Wan 2.2',
                         'Premium Image Quality',
                         'Up to 8 Images at Once',
                         'Google Veo3',
                         'Creative Characters',
                         'Ruxo generation',
                    ]
               },
               'ultimate': {
                    credits: 2000,
                    features: [
                         '2,000 Credits per month',
                         'Generate up to 2,000 images',
                         'Generate up to 200 videos',
                         'Unlimited concurrent generations',
                         'Image & Video upscaling',
                         'Video Models: Wan 2.2',
                         'Premium Image Quality',
                         'Unlimited Images at Once',
                         'Google Veo3',
                         'Creative Characters',
                         'Ruxo generation',
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
          if (!hasActiveSubscription || !user?.plan_name) {
               return { type: 'new', canSelect: true };
          }
          
          const planTier = getPlanTier(plan.name);
          const planInterval = plan.interval;
          
          // Get user's plan key and interval
          const userPlanKey = getPlanKeyFromDisplayName(user.plan_name);
          
          // If user has yearly subscription, they can only see yearly plans
          if (currentPlanInterval === 'year' && planInterval !== 'year') {
               return { type: 'incompatible', canSelect: false };
          }
          
          // If user has monthly subscription, they can see both monthly and yearly
          // (yearly would be an upgrade)
          
          // Check if this is the exact same plan (same tier AND same interval)
          const isExactMatch = userPlanKey === plan.name.split('_')[0] && 
                              planInterval === currentPlanInterval &&
                              currentPlanInterval !== null;
          
          if (isExactMatch) {
               // This is the user's current plan
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
               if (userPlanKey === plan.name.split('_')[0]) {
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
                              <h2 className="md:text-[48px] text-[32px] mb-3 text-white font-medium leading-[120%] tracking-[-1px]">Choose Your Plan</h2>
                              <p className="text-base font-normal leading-5 text-white/60 tracking-[-0.32px]">Unlock more generations and early access to upcoming features</p>
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
                                             <span className={`${Monthly === "yearly" ? 'text-white/60' : 'text-white/40'}  font-medium text-sm`}>Save 40%</span>
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
                                        
                                        if (isAuthLoading) {
                                             buttonText = "Loading...";
                                        } else if (isProcessing || isManagingPlan) {
                                             buttonText = "Processing...";
                                        } else if (planStatus.type === 'upgrade') {
                                             buttonText = "Upgrade";
                                             buttonOnClick = (e?: React.MouseEvent) => handleSelectPlan(plan.name, e);
                                        } else if (planStatus.type === 'current') {
                                             buttonText = "Manage Subscription";
                                             buttonOnClick = handleManagePlan;
                                        } else if (planStatus.type === 'downgrade' || planStatus.type === 'incompatible') {
                                             // Show "Not Available" for any downgrade or incompatible plan
                                             buttonText = "Not Available";
                                        } else if (planStatus.canSelect) {
                                             buttonOnClick = (e?: React.MouseEvent) => handleSelectPlan(plan.name, e);
                                        }
                                        
                                        // Dim any card that shows "Not Available"
                                        const shouldDim = isAuthLoading ? false : (buttonText === "Not Available");
                                        
                                        const cardProps = {
                                             plan: displayName,
                                             price: formatPrice(plan.amount_dollars),
                                             originalPrice: originalPrice,
                                             duration: Monthly === "monthly" ? "/month" : "/year",
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
                    </div>
               </section>
          </>
     )
}

export default page
