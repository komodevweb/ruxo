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
        // User is now authenticated, redirect to homepage
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
          
          console.log('[OAUTH FRONTEND] Redirect_to URL:', redirectTo);
          console.log('[OAUTH FRONTEND] Calling backend exchange endpoint...');
          
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/auth/oauth/exchange`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              code: oauthCode,
              redirect_to: redirectTo
            }),
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
