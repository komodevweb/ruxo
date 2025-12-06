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
        title="Create your own AI Actor"
        description="Customize visuals, audio, and actions to help you present. Create your very own avatar."
        link="/create-actor"
      />
      <CardFeature
        image={cardImages[1]}
        icon="/images/play-icon.svg"
        title="AI Video Editing"
        description="Add subtitles, music, cuts and transitions in one click."
        link="/video-editing"
      />
      <CardFeature
        image={cardImages[2]}
        icon="/images/Panorama.svg"
        title="Emotion control"
        description="You have full emotion control. Activates how you want it."
        link="/emotion-control"
      />
      <div className="lg:col-start-2">
        <CardFeature
          image={cardImages[3]}
          icon="/images/notepad-icon.svg"
          title="Location in every language"
          description="Accurate translation in more than 30 languages. Reach the world."
          link="/translation"
        />
      </div>
    </div>
  );
}

