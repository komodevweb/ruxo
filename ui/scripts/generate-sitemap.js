const fs = require('fs');
const path = require('path');

// Get base URL from environment or default to production
const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://ruxo.ai';

// Ensure URL doesn't have trailing slash
const cleanBaseUrl = baseUrl.replace(/\/$/, '');

// Get current date for lastModified
const currentDate = new Date();

// Define all public routes
const routes = [
  {
    url: cleanBaseUrl,
    lastModified: currentDate,
    changeFrequency: 'daily',
    priority: 1.0,
  },
  {
    url: `${cleanBaseUrl}/text-to-video`,
    lastModified: currentDate,
    changeFrequency: 'daily',
    priority: 0.9,
  },
  {
    url: `${cleanBaseUrl}/image-to-video`,
    lastModified: currentDate,
    changeFrequency: 'daily',
    priority: 0.9,
  },
  {
    url: `${cleanBaseUrl}/image`,
    lastModified: currentDate,
    changeFrequency: 'daily',
    priority: 0.9,
  },
  {
    url: `${cleanBaseUrl}/wan-animate`,
    lastModified: currentDate,
    changeFrequency: 'weekly',
    priority: 0.8,
  },
  {
    url: `${cleanBaseUrl}/upgrade`,
    lastModified: currentDate,
    changeFrequency: 'weekly',
    priority: 0.8,
  },
  {
    url: `${cleanBaseUrl}/privacy`,
    lastModified: currentDate,
    changeFrequency: 'monthly',
    priority: 0.5,
  },
  {
    url: `${cleanBaseUrl}/terms`,
    lastModified: currentDate,
    changeFrequency: 'monthly',
    priority: 0.5,
  },
  {
    url: `${cleanBaseUrl}/login`,
    lastModified: currentDate,
    changeFrequency: 'monthly',
    priority: 0.3,
  },
  {
    url: `${cleanBaseUrl}/signup`,
    lastModified: currentDate,
    changeFrequency: 'monthly',
    priority: 0.3,
  },
];

// Generate XML sitemap
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${routes.map(route => `  <url>
    <loc>${route.url}</loc>
    <lastmod>${route.lastModified.toISOString()}</lastmod>
    <changefreq>${route.changeFrequency}</changefreq>
    <priority>${route.priority}</priority>
  </url>`).join('\n')}
</urlset>`;

// Write to public folder
const publicDir = path.join(__dirname, '..', 'public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

const sitemapPath = path.join(publicDir, 'sitemap.xml');
fs.writeFileSync(sitemapPath, sitemap, 'utf8');

console.log(`✅ Sitemap generated at ${sitemapPath}`);
console.log(`   Contains ${routes.length} URLs`);

