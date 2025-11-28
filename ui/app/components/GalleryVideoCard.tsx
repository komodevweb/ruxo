'use client';
import { useRef, useState } from 'react';

interface GalleryVideoCardProps {
  src: string;
  aspectRatio?: string;
  className?: string;
}

const GalleryVideoCard = ({ 
  src, 
  aspectRatio = "aspect-[9/16]", 
  className = "" 
}: GalleryVideoCardProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (videoRef.current) {
      videoRef.current.muted = false;
      videoRef.current.play().catch(e => {
        // Autoplay with sound might fail due to browser policy
        // Fallback to muted play if needed
        if (videoRef.current) {
          videoRef.current.muted = true;
          videoRef.current.play().catch(e2 => console.error('Autoplay failed', e2));
        }
      });
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
      videoRef.current.muted = true;
    }
  };

  return (
    <div 
      className={`relative rounded-2xl overflow-hidden bg-[#1A1D24] border border-white/10 cursor-pointer group ${aspectRatio} ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <video 
        ref={videoRef}
        src={src}
        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
        loop
        muted
        playsInline
      />
      
      {/* Default Overlay (Play Icon) */}
      <div className={`absolute inset-0 flex items-center justify-center bg-black/20 transition-opacity duration-300 ${isHovered ? 'opacity-0' : 'opacity-100'}`}>
        <div className="w-12 h-12 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
           <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
             <path d="M8 5v14l11-7z" />
           </svg>
        </div>
      </div>

      {/* Hover Overlay (Sound Icon + Gradient) */}
      <div className={`absolute inset-0 pointer-events-none bg-gradient-to-t from-black/60 via-transparent to-transparent transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute bottom-3 right-3">
          <div className="p-2 rounded-full bg-black/40 backdrop-blur-md border border-white/10">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GalleryVideoCard;

