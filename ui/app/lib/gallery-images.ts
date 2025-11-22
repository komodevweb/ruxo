// Gallery images shared across components - only from images/home (WebP format for faster loading)
export const allImages = [
  "/images/home/image-0416902a.webp",
  "/images/home/image-192c68d5.webp",
  "/images/home/image-1d6f6d2e.webp",
  "/images/home/image-2240b12a.webp",
  "/images/home/image-25ce21a6.webp",
  "/images/home/image-28a88dc4.webp",
  "/images/home/image-2cf246b3.webp",
  "/images/home/image-3281a62a.webp",
  "/images/home/image-34ebaa51.webp",
  "/images/home/image-3729ea1a.webp",
  "/images/home/image-3dc3910e.webp",
  "/images/home/image-41843806.webp",
  "/images/home/image-494508f0.webp",
  "/images/home/image-4b754bfb.webp",
  "/images/home/image-4ebcffb3.webp",
  "/images/home/image-51511f6b.webp",
  "/images/home/image-540269c4.webp",
  "/images/home/image-6a087825.webp",
  "/images/home/image-6edd21d2.webp",
  "/images/home/image-712dea83.webp",
  "/images/home/image-82b119c9.webp",
  "/images/home/image-8dda818d.webp",
  "/images/home/image-8e17df35.webp",
  "/images/home/image-94193158.webp",
  "/images/home/image-a7fb2165.webp",
  "/images/home/image-a992407c.webp",
  "/images/home/image-ad94816a.webp",
  "/images/home/image-adceb3cd.webp",
  "/images/home/image-b5945ee1.webp",
  "/images/home/image-b61baa04.webp",
  "/images/home/image-b79dc716.webp",
  "/images/home/image-bb69a01b.webp",
  "/images/home/image-c045804a.webp",
  "/images/home/image-cd0e890d.webp",
  "/images/home/image-d7af3ce3.webp",
  "/images/home/image-d8130cc6.webp",
  "/images/home/image-d8c16574.webp",
  "/images/home/image-dc291b7a.webp",
  "/images/home/image-ec7d7d8d.webp",
];

// Helper function to get random unique images
export function getRandomImages(count: number): string[] {
  const shuffled = [...allImages];
  // Fisher-Yates shuffle for truly random selection
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled.slice(0, count);
}
