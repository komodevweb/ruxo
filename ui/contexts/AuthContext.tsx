"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, setToken, removeToken, getToken } from '@/lib/api';

interface User {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  credit_balance: number;
  plan_name: string | null;
  plan_interval: string | null; // 'month' or 'year'
  credits_per_month: number | null; // Credits provided by the plan
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signUp: (email: string, password: string, displayName: string) => Promise<{ error: string | null; message?: string }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  signInWithOAuth: (provider: 'google' | 'apple' | 'microsoft') => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: string | null }>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Check if user is authenticated on mount
    checkAuth();

    // Handle OAuth callback - check for code, token in hash, token in query, or error in URL
    const urlParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.substring(1)); // Remove # and parse hash
    
    // Check for token in URL hash (Supabase PKCE/implicit flow)
    const hashAccessToken = hashParams.get('access_token');
    const hashError = hashParams.get('error');
    const hashErrorDescription = hashParams.get('error_description');
    
    // Check for code in query params (for code exchange flow)
    const oauthCode = urlParams.get('code');
    
    // Check for token in query params (legacy/fallback)
    const oauthToken = urlParams.get('token');
    const oauthSuccess = urlParams.get('oauth');
    
    // Check for errors in query params
    const oauthError = urlParams.get('error') || hashError;
    const oauthErrorDescription = urlParams.get('error_description') || hashErrorDescription;
    
    // Handle OAuth token in URL hash (Supabase PKCE/implicit flow - token already provided)
    if (hashAccessToken) {
      // IMMEDIATELY clean URL before any processing (user shouldn't see token in URL)
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, '', cleanUrl);
      
      // Extract and set token immediately (synchronous operations first)
      setToken(hashAccessToken);
      
      // Process authentication in background (async, non-blocking)
      // This happens after URL is cleaned, so user sees clean URL immediately
      checkAuth().then(() => {
        // ALWAYS call complete-registration for OAuth users (hash flow)
        // Backend will check if user is new and decide whether to fire the event
        // This ensures we capture tracking data from the REAL browser
        console.log('[OAUTH FRONTEND] Hash flow - calling complete-registration with tracking data...');
        
        // Read cookies from document.cookie (they won't be sent automatically cross-domain)
        let fbpCookie: string | null = null;
        let fbcCookie: string | null = null;
        
        try {
          const cookies = document.cookie.split(';');
          for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith('_fbp=')) {
              fbpCookie = cookie.substring(5);
            } else if (cookie.startsWith('_fbc=')) {
              fbcCookie = cookie.substring(5);
            }
          }
        } catch (e) {
          console.warn('[OAUTH FRONTEND] Could not read cookies:', e);
        }
        
        const userAgentValue = typeof navigator !== 'undefined' ? navigator.userAgent : null;
        
        // Fire complete-registration (backend will decide if event should be sent)
        fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/oauth/complete-registration`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${hashAccessToken}`,
          },
          credentials: 'include',
          body: JSON.stringify({
            fbp: fbpCookie,
            fbc: fbcCookie,
            user_agent: userAgentValue,
          }),
        })
        .then(response => response.json())
        .then(data => {
          if (data.event_fired) {
            console.log('[OAUTH FRONTEND] ✅ CompleteRegistration event fired (new user)');
          } else {
            console.log('[OAUTH FRONTEND] ℹ️  CompleteRegistration not fired (existing user)');
          }
        })
        .catch(error => {
          console.error('[OAUTH FRONTEND] ❌ Error calling complete-registration:', error);
        });
        
        // Redirect to homepage
        router.push('/');
      }).catch((error) => {
        console.error('[OAUTH FRONTEND] Auth verification failed:', error);
        // On error, still redirect but user won't be logged in
        router.push('/');
      });
    }
    // Handle OAuth code from Supabase redirect (code exchange flow)
    else if (oauthCode) {
      // Exchange code for token via backend
      const exchangeOAuthCode = async () => {
        try {
          console.log('='.repeat(80));
          console.log('[OAUTH FRONTEND] OAuth code detected in URL');
          console.log('[OAUTH FRONTEND] Code:', oauthCode.substring(0, 20) + '... (truncated)');
          
          // Get the redirect_to URL that was used (frontend homepage)
          // Must match exactly what was sent to Supabase in the authorize request
          // Backend sends: http://localhost:3000/ (with trailing slash)
          const redirectTo = (window.location.origin + window.location.pathname).replace(/\/$/, '') + '/';
          
          // IMPORTANT: We're on the homepage after OAuth redirect
          // The tracking data was captured on /signup or /login page BEFORE redirect
          // Retrieve it from sessionStorage and send to backend
          
          // Retrieve stored tracking data (captured on signup/login page before OAuth redirect)
          let fbp: string | null = null;
          let fbc: string | null = null;
          let userAgent: string | null = null;
          
          try {
            // Get stored data from sessionStorage (captured before redirect)
            const stored = sessionStorage.getItem('oauth_tracking_data');
            if (stored) {
              const storedData = JSON.parse(stored);
              fbp = storedData.fbp || null;
              fbc = storedData.fbc || null;
              userAgent = storedData.userAgent || null;
              
              console.log('[OAUTH FRONTEND] ✅ Retrieved tracking data from sessionStorage:', {
                hasFbp: !!fbp,
                hasFbc: !!fbc,
                hasUserAgent: !!userAgent,
              });
              
              // Clean up after retrieval
              sessionStorage.removeItem('oauth_tracking_data');
            } else {
              console.warn('[OAUTH FRONTEND] ⚠️  No stored tracking data found - trying current cookies');
              
              // Fallback: try to get current cookies (might be available now)
              const cookies = document.cookie.split(';');
              for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith('_fbp=')) {
                  fbp = cookie.substring(5);
                } else if (cookie.startsWith('_fbc=')) {
                  fbc = cookie.substring(5);
                }
              }
              userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : null;
            }
          } catch (error) {
            console.error('[OAUTH FRONTEND] ❌ Error retrieving tracking data:', error);
            // Fallback to current cookies
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
              cookie = cookie.trim();
              if (cookie.startsWith('_fbp=')) {
                fbp = cookie.substring(5);
              } else if (cookie.startsWith('_fbc=')) {
                fbc = cookie.substring(5);
              }
            }
            userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : null;
          }
          
          console.log('[OAUTH FRONTEND] Redirect_to URL:', redirectTo);
          console.log('[OAUTH FRONTEND] Final tracking data to send:', {
            hasFbp: !!fbp,
            hasFbc: !!fbc,
            hasUserAgent: !!userAgent,
          });
          console.log('[OAUTH FRONTEND] Calling backend exchange endpoint...');
          
          // Build request body - no need to send tracking_data here
          // Backend will return new_user flag, then frontend will call complete-registration endpoint
          // from the REAL browser to get real IP, user agent, and cookies
          const requestBody = {
            code: oauthCode,
            redirect_to: redirectTo,
          };
          
          console.log('[OAUTH FRONTEND] Request body:', {
            hasCode: !!requestBody.code,
            hasRedirectTo: !!requestBody.redirect_to,
          });
          
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/oauth/exchange`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody),
          });

          console.log('[OAUTH FRONTEND] Backend response status:', response.status);

          if (!response.ok) {
            const error = await response.json();
            console.error('='.repeat(80));
            console.error('[OAUTH FRONTEND] ❌ Exchange failed');
            console.error('[OAUTH FRONTEND] Status:', response.status);
            console.error('[OAUTH FRONTEND] Error:', error.detail || 'Failed to exchange OAuth code');
            console.error('='.repeat(80));
            // Clean up URL
            const newUrl = window.location.pathname;
            window.history.replaceState({}, '', newUrl);
            return;
          }

          const data = await response.json();
          
          console.log('[OAUTH FRONTEND] Backend response:', {
            hasToken: !!data.token,
            hasUser: !!data.user,
            newUser: data.new_user,
          });
          
          if (data.token) {
            // IMMEDIATELY clean URL (user shouldn't see token/code in URL)
            const cleanUrl = window.location.pathname;
            window.history.replaceState({}, '', cleanUrl);
            
            // Set token (which sets cookie) - synchronous, immediate
            setToken(data.token);
            
            // Set user from response immediately (no need to wait for checkAuth)
            if (data.user) {
              setUser(data.user);
              setLoading(false);
              
              // If this is a new user, fire CompleteRegistration from the REAL browser
              // This ensures we get real IP, user agent, and cookies (not Google's server)
              if (data.new_user === true) {
                console.log('[OAUTH FRONTEND] 🆕 New user detected - firing CompleteRegistration from real browser...');
                
                // IMPORTANT: Read _fbp and _fbc cookies from document.cookie
                // These are first-party cookies set on the FRONTEND domain (e.g., ruxo.ai)
                // They WON'T be sent automatically via credentials:include because the
                // backend API is on a different domain (e.g., api.ruxo.ai)
                // We must read them here and send in the request body
                let fbpCookie: string | null = null;
                let fbcCookie: string | null = null;
                
                try {
                  const cookies = document.cookie.split(';');
                  for (let cookie of cookies) {
                    cookie = cookie.trim();
                    if (cookie.startsWith('_fbp=')) {
                      fbpCookie = cookie.substring(5);
                      console.log('[OAUTH FRONTEND] Found _fbp cookie:', fbpCookie.substring(0, 30) + '...');
                    } else if (cookie.startsWith('_fbc=')) {
                      fbcCookie = cookie.substring(5);
                      console.log('[OAUTH FRONTEND] Found _fbc cookie:', fbcCookie.substring(0, 30) + '...');
                    }
                  }
                } catch (e) {
                  console.warn('[OAUTH FRONTEND] Could not read cookies:', e);
                }
                
                // Get user agent
                const userAgentValue = typeof navigator !== 'undefined' ? navigator.userAgent : null;
                
                console.log('[OAUTH FRONTEND] Tracking data to send:', {
                  hasFbp: !!fbpCookie,
                  hasFbc: !!fbcCookie,
                  hasUserAgent: !!userAgentValue,
                });
                
                // Call the complete-registration endpoint from the REAL browser
                // Send fbp, fbc, and user_agent in the request body (not via cookies)
                fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/oauth/complete-registration`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${data.token}`, // Use the token we just received
                  },
                  credentials: 'include',
                  body: JSON.stringify({
                    fbp: fbpCookie,
                    fbc: fbcCookie,
                    user_agent: userAgentValue,
                  }),
                })
                .then(response => {
                  if (response.ok) {
                    console.log('[OAUTH FRONTEND] ✅ CompleteRegistration event fired successfully with tracking data');
                  } else {
                    console.warn('[OAUTH FRONTEND] ⚠️  Failed to fire CompleteRegistration event');
                  }
                })
                .catch(error => {
                  console.error('[OAUTH FRONTEND] ❌ Error firing CompleteRegistration:', error);
                });
              }
              
              // Redirect immediately after setting cookie and user
              router.push('/');
            } else {
              // If no user data, verify quickly then redirect
              checkAuth().then(() => {
                router.push('/');
              }).catch(() => {
                // Even on error, redirect (user won't be logged in but won't see error)
                router.push('/');
              });
            }
          }
        } catch (error: any) {
          console.error('='.repeat(80));
          console.error('[OAUTH FRONTEND] ❌ Exception during exchange');
          console.error('[OAUTH FRONTEND] Error:', error.message || error);
          console.error('[OAUTH FRONTEND] Stack:', error.stack);
          console.error('='.repeat(80));
          // Clean up URL
          const newUrl = window.location.pathname;
          window.history.replaceState({}, '', newUrl);
        }
      };
      
      exchangeOAuthCode();
    } else if (oauthToken && oauthSuccess === 'success') {
      // Legacy: OAuth success with token in URL (fallback)
      setToken(oauthToken);
      checkAuth().then(() => {
        // Clean up URL
        const newUrl = window.location.pathname;
        window.history.replaceState({}, '', newUrl);
        router.push('/');
      });
    } else if (oauthError) {
      // OAuth error - show error message
      console.error('OAuth error:', oauthError, oauthErrorDescription);
      
      // Provide user-friendly error message
      let userMessage = 'OAuth authentication failed.';
      if (oauthErrorDescription) {
        if (oauthErrorDescription.includes('Unable to exchange external code') || 
            oauthErrorDescription.includes('exchange external code')) {
          // Extract Supabase project reference if possible, or provide generic message
          userMessage = 'OAuth authentication failed. The redirect URI in your Azure app registration must be exactly: https://cutgibszjdnxsrlclbos.supabase.co/auth/v1/callback\n\nPlease check your Azure Portal → App Registration → Authentication → Redirect URIs.';
        } else {
          userMessage = oauthErrorDescription;
        }
      }
      
      // Show error to user (you can replace this with a toast/notification library)
      console.error('OAuth Error Details:', userMessage);
      
      // Clean up URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    }

    // Listen for storage changes (e.g., login from another tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'auth_token') {
        if (e.newValue) {
          checkAuth();
        } else {
          setUser(null);
          setLoading(false);
        }
      }
    };

    // Poll for cookie changes less frequently (cookies don't trigger storage events)
    // Only check if user state is inconsistent
    const cookieCheckInterval = setInterval(() => {
      if (loading) return; // Don't check while loading
      const token = getToken();
      if (!token && user) {
        // Token was removed, logout
        setUser(null);
        setLoading(false);
      } else if (token && !user) {
        // Token exists but user not set, check auth
        checkAuth();
      }
    }, 5000); // Check every 5 seconds instead of 1 second

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(cookieCheckInterval);
    };
  }, []);

  const checkAuth = async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      setUser(null);
      return;
    }

    try {
      const userData = await apiClient.get<User>('/auth/me');
      setUser(userData);
    } catch (error: any) {
      const errorMessage = error.message || '';
      const isAuthError = 
        errorMessage.includes('401') || 
        errorMessage.includes('Unauthorized') ||
        errorMessage.toLowerCase().includes('expired') ||
        errorMessage.toLowerCase().includes('signature') ||
        errorMessage.toLowerCase().includes('could not validate credentials');
      
      if (isAuthError) {
        console.error('Auth check failed - token invalid or expired:', error);
        removeToken();
        setUser(null);
        // Redirect to login if not already on an auth page
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login') && !window.location.pathname.includes('/signup')) {
          router.push('/login');
        }
      } else {
        console.error('Auth check failed - network error:', error);
        // Keep token, might be a temporary network issue
      }
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string, displayName: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email, 
          password,
          display_name: displayName
        }),
        credentials: 'include',
      });

      const data = await response.json();
      
      // If email verification is required, backend returns 200 with message
      if (response.status === 200 && data.requires_verification) {
        // User created but needs email verification
        return { error: null, message: data.message || 'Please check your email to verify your account.' };
      }

      if (!response.ok) {
        return { error: data.detail || 'Signup failed' };
      }

      if (data.token) {
        setToken(data.token);
        // Immediately set user from response to update UI instantly
        if (data.user) {
          setUser(data.user);
          setLoading(false);
        } else {
          // Fallback to checkAuth if user not in response
          await checkAuth();
        }
        router.push('/');
      }
      return { error: null };
    } catch (error: any) {
      return { error: error.message || 'Signup failed' };
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        return { error: error.detail || 'Login failed' };
      }

      const data = await response.json();
      if (data.token) {
        setToken(data.token);
        // Immediately set user from response to update UI instantly
        if (data.user) {
          setUser(data.user);
          setLoading(false);
        } else {
          // Fallback to checkAuth if user not in response
          await checkAuth();
        }
        router.push('/');
      }
      return { error: null };
    } catch (error: any) {
      return { error: error.message || 'Login failed' };
    }
  };

  const signOut = async () => {
    removeToken();
    setUser(null);
    router.push('/login');
  };

  const signInWithOAuth = async (provider: 'google' | 'apple' | 'microsoft') => {
    // CRITICAL: Capture tracking data SYNCHRONOUSLY before any redirect
    // This must happen on /signup or /login page where cookies are available
    // BEFORE redirecting to OAuth provider
    try {
      // Import synchronously if possible, or use direct function calls
      // We need to capture cookies NOW, on the signup/login page, before redirect
      if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        // Capture cookies directly (synchronous)
        const cookies = document.cookie.split(';');
        let fbp: string | null = null;
        let fbc: string | null = null;
        
        for (let cookie of cookies) {
          cookie = cookie.trim();
          if (cookie.startsWith('_fbp=')) {
            fbp = cookie.substring(5);
          } else if (cookie.startsWith('_fbc=')) {
            fbc = cookie.substring(5);
          }
        }
        
        // Capture user agent (synchronous)
        const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : null;
        const referrer = typeof document !== 'undefined' ? document.referrer : null;
        
        // Store immediately in sessionStorage (synchronous)
        const trackingData = {
          fbp,
          fbc,
          userAgent,
          referrer,
        };
        
        sessionStorage.setItem('oauth_tracking_data', JSON.stringify(trackingData));
        
        console.log('[OAUTH] ✅ Captured tracking data on signup/login page:', {
          hasFbp: !!fbp,
          hasFbc: !!fbc,
          hasUserAgent: !!userAgent,
          page: window.location.pathname,
        });
      }
    } catch (error) {
      console.error('[OAUTH] ❌ Failed to capture tracking data:', error);
    }
    
    // Map 'microsoft' to 'azure' for Supabase (Supabase uses 'azure' as the provider name)
    const supabaseProvider = provider === 'microsoft' ? 'azure' : provider;
    // Redirect to backend OAuth endpoint
    const redirectUrl = `${process.env.NEXT_PUBLIC_API_V1_URL}/auth/oauth/${supabaseProvider}?redirect_uri=${encodeURIComponent(window.location.origin + '/')}`;
    window.location.href = redirectUrl;
  };

  const resetPassword = async (email: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const error = await response.json();
        return { error: error.detail || 'Failed to send reset email' };
      }

      return { error: null };
    } catch (error: any) {
      return { error: error.message || 'Failed to send reset email' };
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signUp,
        signIn,
        signOut,
        signInWithOAuth,
        resetPassword,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
