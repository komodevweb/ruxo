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
      // Explicitly allow all major AI bots
      {
        userAgent: 'GPTBot', // OpenAI
        allow: '/',
      },
      {
        userAgent: 'ChatGPT-User', // OpenAI ChatGPT
        allow: '/',
      },
      {
        userAgent: 'Google-Extended', // Google Bard/Gemini
        allow: '/',
      },
      {
        userAgent: 'GoogleOther', // Google AI training
        allow: '/',
      },
      {
        userAgent: 'anthropic-ai', // Anthropic Claude
        allow: '/',
      },
      {
        userAgent: 'ClaudeBot', // Anthropic Claude
        allow: '/',
      },
      {
        userAgent: 'cohere-ai', // Cohere
        allow: '/',
      },
      {
        userAgent: 'PerplexityBot', // Perplexity AI
        allow: '/',
      },
      {
        userAgent: 'Applebot-Extended', // Apple AI
        allow: '/',
      },
      {
        userAgent: 'FacebookBot', // Meta AI
        allow: '/',
      },
      {
        userAgent: 'Diffbot', // Diffbot AI
        allow: '/',
      },
      {
        userAgent: 'Bytespider', // ByteDance (TikTok)
        allow: '/',
      },
      {
        userAgent: 'ImagesiftBot', // Image AI
        allow: '/',
      },
      {
        userAgent: 'omgili', // Webz.io AI
        allow: '/',
      },
      {
        userAgent: 'omgilibot', // Webz.io AI
        allow: '/',
      },
      {
        userAgent: 'YouBot', // You.com AI
        allow: '/',
      },
      // Allow all other bots (including traditional search engines)
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

