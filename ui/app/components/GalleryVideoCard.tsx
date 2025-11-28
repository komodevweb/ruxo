'use client';
import { useRef, useState, useEffect } from 'react';

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
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleMouseEnter = () => {
    if (!isMobile && videoRef.current) {
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
    if (!isMobile && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
      videoRef.current.muted = true;
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    if (isMobile && videoRef.current) {
      e.stopPropagation();
      if (videoRef.current.paused) {
        videoRef.current.muted = false;
        videoRef.current.play().catch(console.error);
      } else {
        videoRef.current.pause();
      }
    }
  };

  return (
    <div 
      className={`relative rounded-2xl overflow-hidden bg-[#1A1D24] border border-white/10 cursor-pointer group ${aspectRatio} ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      <video 
        ref={videoRef}
        src={src}
        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
        loop
        muted
        playsInline
        preload="metadata"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onLoadedMetadata={(e) => {
             e.currentTarget.currentTime = 0.1;
        }}
      />
      
      {/* Play Icon Overlay */}
      <div className={`absolute inset-0 flex items-center justify-center pointer-events-none bg-black/20 transition-all duration-300 ${isPlaying ? 'opacity-0' : 'opacity-100'} ${!isMobile ? 'group-hover:opacity-0' : ''}`}>
        <svg className="w-10 h-10 md:w-12 md:h-12 text-white/80 drop-shadow-lg" fill="currentColor" viewBox="0 0 24 24">
           <path d="M8 5v14l11-7z" />
        </svg>
      </div>

      {/* Sound Icon (Desktop only, on hover) */}
      {!isMobile && (
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-black/60 via-transparent to-transparent transition-opacity duration-300 opacity-0 group-hover:opacity-100">
        <div className="absolute bottom-3 right-3">
          <div className="p-2 rounded-full bg-black/40 backdrop-blur-md border border-white/10">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
          </div>
        </div>
      </div>
      )}
    </div>
  );
};

export default GalleryVideoCard;
