"use client";
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { getRandomImages } from '../lib/gallery-images';

const modelsData = [
  {
    id: 1,
    title: "Sora 2 Pro",
    description: "Videos with sharp motion and precise prompt control",
    badge: "NEW",
    icon: (
      <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-1.07 3.97-2.1 5.39z"/>
      </svg>
    )
  },
  {
    id: 2,
    title: "G Veo 3.1",
    description: "Flawless audio-video sync with style and character control",
    badge: "NEW",
    icon: (
       <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
         <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
       </svg>
    )
  },
  {
    id: 3,
    title: "G Nano Banana",
    description: "Powerful image editing with perfect character consistency",
    badge: null,
    icon: (
      <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
        <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zm-10-7h2v2h-2zm0-4h2v2h-2z"/>
      </svg>
    )
  },
  {
    id: 4,
    title: "Kling 2.5 Turbo",
    description: "Cinematic motion with precision and depth",
    badge: null,
    icon: (
      <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
      </svg>
    )
  }
];

export default function FeaturedModels() {
  const [models, setModels] = useState(modelsData.map(model => ({ ...model, image: "" })));

  useEffect(() => {
    // Select 4 random unique images for the models
    const images = getRandomImages(4);
    setModels(modelsData.map((model, index) => ({
      ...model,
      image: images[index] || images[0]
    })));
  }, []);

  return (
    <section className="py-12">
      <div className="max-w-[1320px] px-5 mx-auto">
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-medium text-[#cefb16] mb-6 uppercase">FEATURED AI MODELS</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {models.map((model) => (
            <div key={model.id} className="relative group rounded-xl overflow-hidden aspect-[4/5] cursor-pointer border border-white/5 hover:border-white/20 transition-all duration-300">
              {model.image && (
                <Image 
                  src={model.image} 
                  alt={model.title} 
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-105" 
                />
              )}
              {/* Gradient Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent opacity-90"></div>
              
              {/* Badge */}
              {model.badge && (
                <span className="absolute top-4 left-4 bg-blue-1000 text-black text-[10px] font-bold px-2 py-1 rounded-md">
                  {model.badge}
                </span>
              )}

              {/* Content */}
              <div className="absolute bottom-0 left-0 w-full p-5">
                <div className="flex items-center gap-2 mb-2">
                  {model.icon}
                  <h3 className="text-lg font-bold text-white leading-tight">{model.title}</h3>
                </div>
                <p className="text-sm text-white/70 leading-snug font-medium">
                  {model.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


