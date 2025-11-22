"use client";
import Image from 'next/image';
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

import { allImages } from '../lib/gallery-images';

const aspectRatios = [
  "aspect-square",
  "aspect-[4/3]",
  "aspect-[3/4]",
  "aspect-[16/9]",
  "aspect-[9/16]",
  "aspect-[4/5]",
  "aspect-[5/4]",
  "aspect-[3/2]",
  "aspect-[2/3]",
];

// Shuffle array function
function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Fixed order for SSR (deterministic)
const MAX_IMAGES = 20;
const fixedImages = allImages.slice(0, MAX_IMAGES).map((src, index) => ({
  src,
  aspect: aspectRatios[index % aspectRatios.length],
}));

export default function ImageGallery() {
  const { user } = useAuth();
  const router = useRouter();
  const [images, setImages] = useState(fixedImages);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // Only shuffle on client side after mount - use requestIdleCallback for better performance
    setIsMounted(true);
    const shuffleAndSetImages = () => {
      const shuffledImages = shuffleArray(allImages);
      const shuffled = shuffledImages.slice(0, MAX_IMAGES).map((src, index) => ({
        src,
        aspect: aspectRatios[index % aspectRatios.length],
      }));
      setImages(shuffled);
    };

    // Use requestIdleCallback if available, otherwise setTimeout
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      requestIdleCallback(shuffleAndSetImages, { timeout: 1000 });
    } else {
      setTimeout(shuffleAndSetImages, 100);
    }
  }, []);

  return (
    <section className="py-12 relative">
      <div className="max-w-[1320px] px-5 mx-auto relative">
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-medium text-[#cefb16] mb-6 uppercase">WHAT YOU CAN CREATE</h2>
        <div className="columns-2 md:columns-4 gap-2 space-y-2 relative">
          {images.map((image, index) => (
            <div 
              key={index} 
              onClick={() => {
                if (!user) {
                  router.push('/signup');
                }
              }}
              className={`break-inside-avoid relative ${image.aspect} overflow-hidden rounded-xl group cursor-pointer mb-2`}
            >
              <Image
                src={image.src}
                alt={`Gallery image ${index + 1}`}
                fill
                loading={index < 4 ? "eager" : "lazy"}
                priority={index < 4}
                quality={85}
                sizes="(max-width: 768px) 50vw, (max-width: 1024px) 25vw, 25vw"
                className="object-cover transition-transform duration-300 group-hover:scale-105"
              />
            </div>
          ))}
        </div>
        {/* Fade out overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-black-1100 via-black-1100/60 to-transparent pointer-events-none"></div>
      </div>
    </section>
  );
}

