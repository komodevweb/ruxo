/**
 * Tracking Helpers
 * 
 * Utilities to capture and preserve tracking data (Facebook Pixel cookies, user agent, etc.)
 * across OAuth redirects where cookies might be lost.
 */

/**
 * Get Facebook Pixel cookies (_fbp, _fbc) from document.cookie
 */
export function getFacebookCookies(): { fbp: string | null; fbc: string | null } {
  if (typeof document === 'undefined') {
    return { fbp: null, fbc: null };
  }

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

  return { fbp, fbc };
}

/**
 * Capture all tracking data available on the frontend
 * This includes Facebook Pixel cookies, user agent, and referrer
 */
export function captureTrackingData(): {
  fbp: string | null;
  fbc: string | null;
  userAgent: string | null;
  referrer: string | null;
} {
  const { fbp, fbc } = getFacebookCookies();
  
  return {
    fbp,
    fbc,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
    referrer: typeof document !== 'undefined' ? document.referrer : null,
  };
}

/**
 * Store tracking data in sessionStorage before OAuth redirect
 * SessionStorage persists across redirects within the same tab
 */
export function storeTrackingDataForOAuth(): void {
  if (typeof window === 'undefined') return;
  
  try {
    const trackingData = captureTrackingData();
    sessionStorage.setItem('oauth_tracking_data', JSON.stringify(trackingData));
    
    console.log('[TRACKING] Stored tracking data for OAuth:', {
      hasFbp: !!trackingData.fbp,
      hasFbc: !!trackingData.fbc,
      hasUserAgent: !!trackingData.userAgent,
      hasReferrer: !!trackingData.referrer,
    });
    
    // Verify it was stored
    const stored = sessionStorage.getItem('oauth_tracking_data');
    if (!stored) {
      console.error('[TRACKING] ❌ Failed to store tracking data in sessionStorage');
    } else {
      console.log('[TRACKING] ✅ Verified tracking data stored successfully');
    }
  } catch (error) {
    console.error('[TRACKING] ❌ Error storing tracking data:', error);
  }
}

/**
 * Retrieve tracking data from sessionStorage after OAuth callback
 * Returns null if no data was stored
 */
export function getStoredTrackingData(): {
  fbp: string | null;
  fbc: string | null;
  userAgent: string | null;
  referrer: string | null;
} | null {
  if (typeof window === 'undefined') return null;
  
  try {
    const stored = sessionStorage.getItem('oauth_tracking_data');
    if (!stored) {
      console.warn('[TRACKING] ⚠️  No stored tracking data found in sessionStorage');
      return null;
    }
    
    const data = JSON.parse(stored);
    console.log('[TRACKING] ✅ Retrieved stored tracking data:', {
      hasFbp: !!data.fbp,
      hasFbc: !!data.fbc,
      hasUserAgent: !!data.userAgent,
      hasReferrer: !!data.referrer,
      fbpValue: data.fbp ? data.fbp.substring(0, 20) + '...' : null,
      fbcValue: data.fbc ? data.fbc.substring(0, 20) + '...' : null,
    });
    
    // Clean up after retrieval
    sessionStorage.removeItem('oauth_tracking_data');
    
    return data;
  } catch (error) {
    console.error('[TRACKING] ❌ Failed to retrieve stored tracking data:', error);
    return null;
  }
}

