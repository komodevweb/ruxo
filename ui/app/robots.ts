import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  // Get base URL from environment or default to production
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 
                  process.env.NEXT_PUBLIC_VERCEL_URL ? 
                    `https://${process.env.NEXT_PUBLIC_VERCEL_URL}` : 
                    'https://ruxo.ai'
  
  // Ensure URL doesn't have trailing slash
  const cleanBaseUrl = baseUrl.replace(/\/$/, '')
  
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/settings',
          '/verify-email',
          '/forgot-password',
          '/login-email',
          '/signup-email',
          '/signup-password',
        ],
      },
    ],
    sitemap: `${cleanBaseUrl}/sitemap.xml`,
  }
}

