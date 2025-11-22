// API URL: Use environment variable if set, otherwise fallback to localhost for local development
// In production, NEXT_PUBLIC_API_V1_URL should be set to your production backend URL
const API_URL = process.env.NEXT_PUBLIC_API_V1_URL || 'http://localhost:8000/api/v1';

// Only warn in production-like environments (not localhost)
if (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_V1_URL) {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    console.warn('NEXT_PUBLIC_API_V1_URL is not set. Using default localhost URL may cause issues in production.');
  }
}

export interface ApiError {
  detail: string;
}

// Store token in cookies
const TOKEN_KEY = 'auth_token';
const COOKIE_EXPIRY_DAYS = 7; // 7 days expiry

// Cookie helper functions
function setCookie(name: string, value: string, days: number) {
  if (typeof document === 'undefined' || !value) {
    return;
  }
  
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  const secure = window.location.protocol === 'https:' ? ';Secure' : '';
  const cookieString = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;SameSite=Lax${secure}`;
  
  document.cookie = cookieString;
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  
  const nameEQ = name + '=';
  const ca = document.cookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) {
      const value = c.substring(nameEQ.length, c.length);
      return decodeURIComponent(value);
    }
  }
  return null;
}

function deleteCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
}

export function getToken(): string | null {
  // Try cookie first
  const cookieToken = getCookie(TOKEN_KEY);
  if (cookieToken) {
    return cookieToken;
  }
  
  // Fallback to localStorage for migration (one-time)
  if (typeof window !== 'undefined') {
    const localToken = localStorage.getItem(TOKEN_KEY);
    if (localToken) {
      // Migrate to cookie (avoiding circular call)
      setCookie(TOKEN_KEY, localToken, COOKIE_EXPIRY_DAYS);
      localStorage.removeItem(TOKEN_KEY);
      return localToken;
    }
  }
  
  return null;
}

export function setToken(token: string): void {
  if (!token) {
    return;
  }
  
  // Store in cookie immediately (synchronous)
  setCookie(TOKEN_KEY, token, COOKIE_EXPIRY_DAYS);
  
  // Also keep in localStorage as backup
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function removeToken(): void {
  // Remove from cookie
  deleteCookie(TOKEN_KEY);
  // Remove from localStorage
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): HeadersInit {
    const token = getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async get<T>(endpoint: string): Promise<T> {
    const headers = this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const errorMessage = error.detail || `HTTP error! status: ${response.status}`;
      
      // Check if it's an authentication error (401 or expired token)
      if (response.status === 401 || errorMessage.toLowerCase().includes('expired') || errorMessage.toLowerCase().includes('signature')) {
        // Clear expired token
        removeToken();
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const headers = this.getAuthHeaders();
    
    try {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include',
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const errorMessage = error.detail || `HTTP error! status: ${response.status}`;
      
      // Check if it's an authentication error (401 or expired token)
      if (response.status === 401 || errorMessage.toLowerCase().includes('expired') || errorMessage.toLowerCase().includes('signature')) {
        // Clear expired token
        removeToken();
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
    } catch (error) {
      // Handle network errors (CORS, connection refused, etc.)
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        const errorMessage = `Network error: Unable to connect to API at ${this.baseUrl}. Please check if the backend server is running.`;
        console.error(errorMessage, error);
        throw new Error(errorMessage);
      }
      // Re-throw other errors
      throw error;
    }
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    const headers = this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include',
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const errorMessage = error.detail || `HTTP error! status: ${response.status}`;
      
      // Check if it's an authentication error (401 or expired token)
      if (response.status === 401 || errorMessage.toLowerCase().includes('expired') || errorMessage.toLowerCase().includes('signature')) {
        // Clear expired token
        removeToken();
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const headers = this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const errorMessage = error.detail || `HTTP error! status: ${response.status}`;
      
      // Check if it's an authentication error (401 or expired token)
      if (response.status === 401 || errorMessage.toLowerCase().includes('expired') || errorMessage.toLowerCase().includes('signature')) {
        // Clear expired token
        removeToken();
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
