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
 * @param options - Optional tracking options including plan details
 */
export async function trackInitiateCheckout(options?: {
  eventSource?: string;
  value?: number;
  currency?: string;
  contentId?: string;
  contentName?: string;
  contentType?: string;
}): Promise<void> {
  try {
    // Log detailed call information
    console.log('🔔 trackInitiateCheckout called', {
      source: options?.eventSource || 'unknown',
      value: options?.value,
      currency: options?.currency,
      contentName: options?.contentName,
      timestamp: new Date().toISOString(),
      url: window.location.href,
    });
    
    // Build request body with optional plan details
    const body: Record<string, any> = {};
    if (options?.value !== undefined) body.value = options.value;
    if (options?.currency) body.currency = options.currency;
    if (options?.contentId) body.content_id = options.contentId;
    if (options?.contentName) body.content_name = options.contentName;
    if (options?.contentType) body.content_type = options.contentType;
    
    // Send with body if we have plan details, otherwise send empty
    if (Object.keys(body).length > 0) {
      await apiClient.post('/billing/track-initiate-checkout', body);
    } else {
    await apiClient.post('/billing/track-initiate-checkout');
    }
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

