"use client";

import { useState, useEffect, useRef, memo } from "react";

interface VideoGalleryProps {
  jobs: any[];
  selectedJobId?: string | null;
  loading?: boolean;
  onSelectJob: (job: any) => void;
}

// Separate VideoCard component to handle individual state logic
const VideoCard = memo(({ 
  job, 
  loadingPercentage, 
  onSelectJob, 
  playPromise 
}: { 
  job: any; 
  loadingPercentage?: number; 
  onSelectJob: (job: any) => void;
  playPromise: { current: Promise<void> | undefined };
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [aspectRatioStyle, setAspectRatioStyle] = useState<any>(undefined);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const hasOutput = !!job.output_url;
  const isRunning = (job.status === "pending" || job.status === "running") && !hasOutput;
  const isFailed = job.status === "failed";

  // Determine initial style from metadata
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);

    const getInitialStyle = () => {
      // 1. Check explicit aspect_ratio field (e.g., "9:16")
      if (job.aspect_ratio && typeof job.aspect_ratio === 'string') {
        const [w, h] = job.aspect_ratio.split(':').map(Number);
        if (w && h) return { aspectRatio: `${w}/${h}` };
      }

      // 2. Check resolution field (e.g., "1280*720" or "720x1280")
      if (job.resolution && typeof job.resolution === 'string') {
        if (job.resolution.includes('*')) {
          const [w, h] = job.resolution.split('*').map(Number);
          if (w && h) return { aspectRatio: `${w}/${h}` };
        }
        if (job.resolution.includes('x')) {
          const [w, h] = job.resolution.split('x').map(Number);
          if (w && h) return { aspectRatio: `${w}/${h}` };
        }
      }
      
      // 3. Check separate width/height
      if (job.width && job.height) {
        return { aspectRatio: `${job.width}/${job.height}` };
      }

      // 4. Check size field from text-to-video (e.g., "1280*720")
      if (job.size && typeof job.size === 'string' && job.size.includes('*')) {
          const [w, h] = job.size.split('*').map(Number);
          if (w && h) return { aspectRatio: `${w}/${h}` };
      }
      
      // Default fallback (will be updated by onLoadedMetadata)
      return { aspectRatio: '16/9' };
    };
    
    setAspectRatioStyle(getInitialStyle());

    return () => window.removeEventListener('resize', checkMobile);
  }, [job]);

  const forceDownload = async (url: string, filename: string) => {
    if (isDownloading) return;
    setIsDownloading(true);

    try {
      // Try to use fetch for better blob handling if possible
      const response = await fetch(url);
      const blob = await response.blob();
      
      // Mobile sharing (iOS/Android) - Only use on mobile devices
      if (isMobile && navigator.share && navigator.canShare) {
        try {
          // Force video/mp4 type to ensure iOS recognizes it as a video file
          const file = new File([blob], filename, { type: 'video/mp4' });
          if (navigator.canShare({ files: [file] })) {
            await navigator.share({
              files: [file],
              title: filename,
            });
            return;
          }
        } catch (shareError: any) {
          // Ignore abort/cancel errors (user cancelled share sheet)
          if (shareError.name === 'AbortError') {
            return;
          }
          console.log("Web Share API failed, using fallback", shareError);
        }
      }
      
      // Fallback: Blob URL download (Desktop / Non-sharing Mobile)
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      // Final fallback: Direct link open (fastest but less control)
      console.error("Download failed, opening directly:", error);
      window.open(url, '_blank');
    } finally {
      setIsDownloading(false);
    }
  };

  const togglePlay = (e: React.MouseEvent) => {
    if (hasOutput && videoRef.current) {
      e.stopPropagation();
      const video = videoRef.current;
      if (video.paused) {
        video.play().catch(console.error);
        video.muted = false; // Enable sound on play
      } else {
        video.pause();
      }
    }
  };

  return (
    <div
      onClick={togglePlay}
      className={`relative overflow-hidden rounded-2xl bg-[#1A1D24] border border-white/10 group ${
        hasOutput 
          ? "cursor-pointer hover:border-white/30 hover:shadow-2xl hover:shadow-blue-900/10" 
          : "cursor-not-allowed"
      } transition-all duration-300`}
      style={aspectRatioStyle}
    >
      {hasOutput ? (
        <>
          <video
            ref={videoRef}
            key={job.output_url}
            src={job.output_url}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            muted
            playsInline
            preload="metadata"
            controls={false}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onLoadedMetadata={(e) => {
              try {
                const video = e.currentTarget;
                if (video.videoWidth && video.videoHeight) {
                  setAspectRatioStyle({ 
                    aspectRatio: `${video.videoWidth}/${video.videoHeight}` 
                  });
                }
                video.currentTime = 0.1;
              } catch (err) {
                console.error("Error seeking video:", err);
              }
            }}
          />
          
          {/* Video Preview Overlay on Mobile */}
          {isMobile && !isPlaying && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/20 transition-opacity duration-300 opacity-100 pointer-events-none">
              {/* Video image is visible via the video element itself paused at 0.1s */}
            </div>
          )}
          
          {/* Model Badge - Always visible (non-intrusive) */}
          {(job.model_display_name || job.settings?.model_display_name) && (
            <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md border border-white/10 text-white text-[10px] font-medium px-2.5 py-1 rounded-full z-10 pointer-events-none opacity-100 transition-opacity duration-300 group-hover:opacity-100">
              {job.model_display_name || job.settings?.model_display_name}
            </div>
          )}

          {/* Play Icon Overlay - Shows when paused */}
          {!isPlaying && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none bg-black/20">
              <svg className="w-10 h-10 md:w-12 md:h-12 text-white/80 drop-shadow-lg" fill="currentColor" viewBox="0 0 24 24">
                   <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          )}

            {/* Download Button - Always visible */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                forceDownload(job.output_url, `video-${job.job_id.slice(0, 8)}.mp4`);
              }}
              disabled={isDownloading}
              className={`absolute top-3 right-3 bg-black/50 backdrop-blur-md border border-white/20 text-white w-8 h-8 flex items-center justify-center rounded-full transition-all duration-300 hover:bg-white hover:text-black z-20 ${isDownloading ? 'opacity-70 cursor-wait' : ''}`}
              title="Download Video"
            >
              {isDownloading ? (
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
              )}
            </button>
        </>
      ) : isRunning ? (
        <div className="w-full h-full bg-gray-900/50 flex flex-col items-center justify-center relative">
           <div className="w-12 h-12 rounded-full border-2 border-blue-500/30 border-t-blue-500 animate-spin mb-4"></div>
           <p className="text-sm font-medium text-white/80">
              Generating... {Math.round(loadingPercentage || 0)}%
           </p>
           <div className="absolute bottom-0 left-0 h-1 bg-blue-500/20 w-full">
              <div 
                 className="h-full bg-blue-500 transition-all duration-300"
                 style={{ width: `${Math.round(loadingPercentage || 0)}%` }}
              />
           </div>
        </div>
      ) : isFailed ? (
        <div 
           onClick={(e) => {
             e.stopPropagation();
             onSelectJob(job);
           }}
           className="w-full h-full bg-red-900/20 border border-red-500/30 flex flex-col items-center justify-center p-4 text-center cursor-pointer hover:bg-red-900/30 transition-colors group/failed"
        >
           <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center mb-3 group-hover/failed:bg-red-500/20 transition-colors">
             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-400">
               <circle cx="12" cy="12" r="10"></circle>
               <line x1="15" y1="9" x2="9" y2="15"></line>
               <line x1="9" y1="9" x2="15" y2="15"></line>
             </svg>
           </div>
           <p className="text-sm font-medium text-red-400 mb-1">Generation Failed</p>
           <p className="text-xs text-red-400/60 line-clamp-2 mb-3">{job.error || "An error occurred"}</p>
           <span className="text-[10px] bg-red-500/10 text-red-300 px-2.5 py-1 rounded-full border border-red-500/20 group-hover/failed:bg-red-500/20 transition-colors">Click to Retry</span>
        </div>
      ) : null}
    </div>
  );
});
VideoCard.displayName = "VideoCard";

function VideoGalleryInner({ jobs, selectedJobId, loading = false, onSelectJob }: VideoGalleryProps) {
  if (loading) {
    return (
      <section className="py-12 relative">
        <div className="max-w-[1320px] px-5 mx-auto relative">
          <h2 className="text-xl font-medium text-white mb-6">Gallery</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, idx) => (
              <div key={`skeleton-${idx}`} className="aspect-video relative overflow-hidden rounded-2xl bg-gray-1600/20">
                <div className="w-full h-full bg-gray-1200/30 relative overflow-hidden">
                  <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }
  
  if (!jobs || jobs.length === 0) return null;
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;
  const playPromises = useRef<Record<string, Promise<void> | undefined>>({});

  // Track loading percentages for each running job
  const [loadingPercentages, setLoadingPercentages] = useState<Record<string, number>>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('videoLoadingPercentages');
        if (saved) {
          return JSON.parse(saved);
        }
      } catch (e) {
        console.error('Failed to load saved percentages:', e);
      }
    }
    return {};
  });
  
  const intervalRefs = useRef<Record<string, NodeJS.Timeout>>({});
  
  // Save percentages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('videoLoadingPercentages', JSON.stringify(loadingPercentages));
      } catch (e) {
        console.error('Failed to save percentages:', e);
      }
    }
  }, [loadingPercentages]);
  
  useEffect(() => {
    const timeoutIds: NodeJS.Timeout[] = [];
    
    // Initialize or update percentages for running jobs
    jobs.forEach((job) => {
      const isRunning = (job.status === "pending" || job.status === "running") && !job.output_url;
      const jobId = job.job_id;
      
      if (isRunning) {
        setLoadingPercentages((prev) => {
          if (!(jobId in prev)) {
            return { ...prev, [jobId]: 0 };
          }
          return prev;
        });
        
        if (!intervalRefs.current[jobId]) {
          intervalRefs.current[jobId] = setInterval(() => {
            setLoadingPercentages((prev) => {
              const current = prev[jobId] || 0;
              const remaining = 100 - current;
              const baseIncrement = 0.8;
              const progressFactor = (remaining / 100) * (remaining / 100);
              const increment = baseIncrement * progressFactor + 0.05;
              const newValue = Math.min(99.5, current + increment);
              return { ...prev, [jobId]: newValue };
            });
          }, 100);
        }
      } else {
        if (intervalRefs.current[jobId]) {
          clearInterval(intervalRefs.current[jobId]);
          delete intervalRefs.current[jobId];
        }
        if (job.status === "completed") {
          setLoadingPercentages((prev) => {
            if (prev[jobId] !== 100) {
              return { ...prev, [jobId]: 100 };
            }
            return prev;
          });
          const timeoutId = setTimeout(() => {
            setLoadingPercentages((prev) => {
              const newState = { ...prev };
              delete newState[jobId];
              return newState;
            });
          }, 2000);
          timeoutIds.push(timeoutId);
        } else if (job.status === "failed") {
          setLoadingPercentages((prev) => {
            if (jobId in prev) {
              const newState = { ...prev };
              delete newState[jobId];
              return newState;
            }
            return prev;
          });
        }
      }
    });
    
    return () => {
      Object.values(intervalRefs.current).forEach((interval) => clearInterval(interval));
      timeoutIds.forEach((timeoutId) => clearTimeout(timeoutId));
    };
  }, [jobs]);

  // Process jobs
  const processedJobs = jobs
    .filter((job: any, index: number, self: any[]) => 
      index === self.findIndex((j: any) => j.job_id === job.job_id)
    )
    .filter((job: any) => {
      const hasOutput = !!job.output_url;
      const isRunning = (job.status === "pending" || job.status === "running") && !hasOutput;
      const isFailed = job.status === "failed";
      return hasOutput || isRunning || isFailed;
    });

  const totalPages = Math.ceil(processedJobs.length / itemsPerPage);
  const currentJobs = processedJobs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );
  
  // Reset page if out of bounds (e.g. filtering reduced count)
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
        setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  // Pagination handlers
  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1);
      // Scroll to top of gallery
      const galleryElement = document.getElementById('video-gallery-section');
      if (galleryElement) {
        galleryElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(prev => prev + 1);
      // Scroll to top of gallery
      const galleryElement = document.getElementById('video-gallery-section');
      if (galleryElement) {
        galleryElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  return (
    <section id="video-gallery-section" className="py-8 relative">
      <div className="max-w-[1320px] px-5 mx-auto relative">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-medium text-white">Gallery</h2>
          {processedJobs.length > 0 && (
            <div className="text-xs text-white/50 font-medium">
              {processedJobs.length} Generation{processedJobs.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {currentJobs.map((job: any) => (
            <VideoCard 
              key={job.job_id}
              job={job}
              loadingPercentage={loadingPercentages[job.job_id]}
              onSelectJob={onSelectJob}
              playPromise={{ current: undefined }} // Pass a fresh ref-like object for local tracking
            />
          ))}
        </div>

        {/* Modern Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center mt-10 gap-2">
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className={`h-10 w-10 rounded-xl flex items-center justify-center border transition-all duration-200 ${
                currentPage === 1
                  ? "border-white/5 text-white/20 cursor-not-allowed bg-white/[0.02]"
                  : "border-white/10 text-white hover:bg-white/10 hover:border-white/20 bg-white/5"
              }`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </button>

            <div className="flex items-center gap-1 px-2">
              <span className="text-sm font-medium text-white">
                {currentPage}
              </span>
              <span className="text-sm text-white/40 mx-1">/</span>
              <span className="text-sm text-white/40">
                {totalPages}
              </span>
            </div>

            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className={`h-10 w-10 rounded-xl flex items-center justify-center border transition-all duration-200 ${
                currentPage === totalPages
                  ? "border-white/5 text-white/20 cursor-not-allowed bg-white/[0.02]"
                  : "border-white/10 text-white hover:bg-white/10 hover:border-white/20 bg-white/5"
              }`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

// Memoized export to prevent re-renders when props haven't changed
const VideoGallery = memo(VideoGalleryInner, (prevProps, nextProps) => {
  if (prevProps.loading !== nextProps.loading) return false;
  if (prevProps.selectedJobId !== nextProps.selectedJobId) return false;
  
  if (prevProps.jobs.length !== nextProps.jobs.length) return false;
  
  const prevKey = prevProps.jobs.map(j => `${j.job_id}:${j.status}:${j.output_url || ''}`).join('|');
  const nextKey = nextProps.jobs.map(j => `${j.job_id}:${j.status}:${j.output_url || ''}`).join('|');
  
  return prevKey === nextKey;
});

export default VideoGallery;
