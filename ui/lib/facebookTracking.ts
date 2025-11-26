/**
 * Facebook Conversions API Tracking Helper
 * 
 * This module provides helper functions to track Facebook conversion events
 * via the backend Conversions API endpoint.
 */

import { apiClient } from './api';

/**
 * Track ViewContent event
 * @param url - Optional URL of the page being viewed
 */
export async function trackViewContent(url?: string): Promise<void> {
  try {
    const params = url ? new URLSearchParams({ url }) : undefined;
    const endpoint = `/billing/track-view-content${params ? `?${params.toString()}` : ''}`;
    console.debug('Tracking ViewContent:', endpoint);
    await apiClient.post(endpoint);
    console.debug('ViewContent tracked successfully');
  } catch (error) {
    // Log error but don't block page functionality
    console.warn('Failed to track ViewContent:', error);
  }
}

/**
 * Track InitiateCheckout event
 * @param eventSource - Optional source identifier to track where the event was triggered from
 */
export async function trackInitiateCheckout(eventSource?: string): Promise<void> {
  try {
    // Log detailed call information
    console.log('🔔 trackInitiateCheckout called', {
      source: eventSource || 'unknown',
      timestamp: new Date().toISOString(),
      url: window.location.href,
    });
    // Trace where this call is coming from
    console.trace('trackInitiateCheckout stack trace');
    
    await apiClient.post('/billing/track-initiate-checkout');
  } catch (error) {
    // Silently fail - tracking should not block page functionality
    console.debug('Failed to track InitiateCheckout:', error);
  }
}

/**
 * Track AddToCart event
 * @param url - Optional URL of the page where the event occurred
 */
export async function trackAddToCart(url?: string): Promise<void> {
  try {
    const params = url ? new URLSearchParams({ url }) : undefined;
    const endpoint = `/billing/track-add-to-cart${params ? `?${params.toString()}` : ''}`;
    console.debug('Tracking AddToCart:', endpoint);
    await apiClient.post(endpoint);
    console.debug('AddToCart tracked successfully');
  } catch (error) {
    // Log error but don't block page functionality
    console.warn('Failed to track AddToCart:', error);
  }
}

