"use client";
import { useState, useEffect } from 'react';
import CardFeature from "./CardFeature";
import { getRandomImages } from '../lib/gallery-images';

export default function HomepageCards() {
  // Start with empty array on both server and client to ensure consistent initial render
  const [cardImages, setCardImages] = useState<string[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // Only set images after mount (client-side only) - use requestIdleCallback for better performance
    setIsMounted(true);
    const setImages = () => {
      const images = getRandomImages(4);
      setCardImages(images);
    };

    // Use requestIdleCallback if available, otherwise setTimeout
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      requestIdleCallback(setImages, { timeout: 500 });
    } else {
      setTimeout(setImages, 50);
    }
  }, []);

  // Show loading skeleton until images are ready (consistent for server and client)
  if (!isMounted || cardImages.length === 0) {
    return (
      <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6">
        <div className="w-full aspect-[4/3] bg-gray-1600/20 rounded-xl animate-pulse"></div>
        <div className="w-full aspect-[4/3] bg-gray-1600/20 rounded-xl animate-pulse"></div>
        <div className="w-full aspect-[4/3] bg-gray-1600/20 rounded-xl animate-pulse"></div>
        <div className="lg:col-start-2 w-full aspect-[4/3] bg-gray-1600/20 rounded-xl animate-pulse"></div>
      </div>
    );
  }

  return (
    <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6">
      <CardFeature
        image={cardImages[0]}
        icon="/images/user-icon.svg"
        title="Image to Video"
        description="Transform your images into dynamic videos with lifelike motion and effects."
        link="/image-to-video"
      />
      <CardFeature
        image={cardImages[1]}
        icon="/images/notepad-icon.svg"
        title="Text to Video"
        description="Turn your text into cinematic video scenes with smart visual storytelling."
        link="/text-to-video"
      />
      <CardFeature
        image={cardImages[2]}
        icon="/images/Panorama.svg"
        title="Text to Image"
        description="Generate original images from text prompts using the latest AI models."
        link="/image"
      />
      <div className="lg:col-start-2">
        <CardFeature
          image={cardImages[3]}
          icon="/images/play-icon.svg"
          title="Wan Animate"
          description="Turn any image into motion with AI-powered animation."
          link="/wan-animate"
        />
      </div>
    </div>
  );
}

