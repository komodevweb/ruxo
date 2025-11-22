"use client";

import { useState, useEffect, useRef } from "react";

interface VideoGalleryProps {
  jobs: any[];
  selectedJobId?: string | null;
  loading?: boolean;
  onSelectJob: (job: any) => void;
}

export default function VideoGallery({ jobs, selectedJobId, loading = false, onSelectJob }: VideoGalleryProps) {
  // Show loading skeletons when loading
  if (loading) {
    return (
      <section className="py-12 relative">
        <div className="max-w-[1320px] px-5 mx-auto relative">
          <h2 className="text-xl font-medium text-white mb-6">Gallery</h2>
          <div className="columns-1 md:columns-2 gap-4 space-y-4 relative">
            {Array.from({ length: 8 }).map((_, idx) => (
              <div key={`skeleton-${idx}`} className="break-inside-avoid relative overflow-hidden rounded-xl mb-4 bg-gray-1600/20" style={{ minHeight: '200px' }}>
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
  
  // Track loading percentages for each running job
  // Load from localStorage on mount to persist across refreshes
  const [loadingPercentages, setLoadingPercentages] = useState<Record<string, number>>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('videoLoadingPercentages');
        if (saved) {
          const parsed = JSON.parse(saved);
          // Only keep percentages for jobs that are still running
          return parsed;
        }
      } catch (e) {
        console.error('Failed to load saved percentages:', e);
      }
    }
    return {};
  });
  const intervalRefs = useRef<Record<string, NodeJS.Timeout>>({});
  const videoRefs = useRef<Record<string, HTMLVideoElement>>({});
  const playPromises = useRef<Record<string, Promise<void> | undefined>>({});
  
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
        // Initialize percentage if not exists (start at 0 or load from localStorage)
        setLoadingPercentages((prev) => {
          if (!(jobId in prev)) {
            return { ...prev, [jobId]: 0 };
          }
          return prev; // Don't update if already exists
        });
        
        // Start or continue loading animation for this job
        if (!intervalRefs.current[jobId]) {
          // Start incrementing percentage with easing (slower as it approaches 100%)
          intervalRefs.current[jobId] = setInterval(() => {
            setLoadingPercentages((prev) => {
              const current = prev[jobId] || 0;
              
              // Easing function: the closer to 100%, the slower it gets
              // Use exponential easing: remaining percentage decreases exponentially
              const remaining = 100 - current;
              const baseIncrement = 0.8; // Base increment per update
              
              // Calculate increment based on remaining percentage
              // As remaining decreases, increment decreases exponentially
              // Formula: increment = base * (remaining/100)^2 + minIncrement
              const progressFactor = (remaining / 100) * (remaining / 100);
              const increment = baseIncrement * progressFactor + 0.05;
              
              const newValue = Math.min(99.5, current + increment); // Cap at 99.5% until actually completed
              return { ...prev, [jobId]: newValue };
            });
          }, 100); // Update every 100ms for smoother animation
        }
      } else {
        // Clean up interval if job is completed or failed
        if (intervalRefs.current[jobId]) {
          clearInterval(intervalRefs.current[jobId]);
          delete intervalRefs.current[jobId];
        }
        // Set to 100% if completed, remove if failed
        if (job.status === "completed") {
          setLoadingPercentages((prev) => {
            // Only update if not already 100
            if (prev[jobId] !== 100) {
              return { ...prev, [jobId]: 100 };
            }
            return prev;
          });
          // Clean up after a delay
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
            // Only update if jobId exists
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
    
    // Cleanup on unmount
    return () => {
      Object.values(intervalRefs.current).forEach((interval) => clearInterval(interval));
      timeoutIds.forEach((timeoutId) => clearTimeout(timeoutId));
    };
  }, [jobs]); // Only depend on jobs, not loadingPercentages

  // Ensure videos show first frame when they load
  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([jobId, video]) => {
      if (video && video.readyState >= 2) {
        // Video has data, ensure first frame is visible
        try {
          // Only reset if the video is PAUSED. If it's playing (hovered), don't touch it!
          // This prevents "flickering" resets when the job list polls in the background.
          if (video.currentTime !== 0 && video.paused) {
            video.currentTime = 0;
          }
        } catch (err) {
          // Ignore
        }
      }
    });
  }, [jobs]);

  const forceDownload = async (url: string, filename: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error("Download failed:", error);
      // Fallback to opening in new tab
      window.open(url, '_blank');
    }
  };

  return (
    <section className="py-12 relative">
      <div className="max-w-[1320px] px-5 mx-auto relative">
        <h2 className="text-xl font-medium text-white mb-6">Gallery</h2>
      <div className="columns-1 md:columns-2 gap-4 space-y-4 relative">
        {jobs
          // Deduplicate by job_id (keep first occurrence)
          .filter((job: any, index: number, self: any[]) => 
            index === self.findIndex((j: any) => j.job_id === job.job_id)
          )
          .filter((job: any) => {
            // Only show jobs that have output OR are currently running
            const hasOutput = !!job.output_url;
            const isRunning = (job.status === "pending" || job.status === "running") && !hasOutput;
            return hasOutput || isRunning;
          })
          .map((job: any) => {
          const hasOutput = !!job.output_url;
          const isCompleted = job.status === "completed" && hasOutput;
          const isSelected = selectedJobId === job.job_id;
          const isRunning = (job.status === "pending" || job.status === "running") && !hasOutput;
          
          return (
            <div
              key={job.job_id}
              onClick={() => {
                if (hasOutput) {
                  onSelectJob(job);
                }
              }}
              onMouseEnter={() => {
                if (hasOutput) {
                  const video = videoRefs.current[job.job_id];
                  if (video) {
                    // Prevent multiple sequences from stacking (fixes flickering on rapid hover)
                    if (playPromises.current[job.job_id]) return;

                    // Create a robust play sequence
                    let playSequence: Promise<void>;
                    const runSequence = async () => {
                      try {
                        // 1. Try to play unmuted (optimistic)
                        video.muted = false;
                        video.currentTime = 0;
                        await video.play();
                      } catch (err: any) {
                        // 2. Handle interruptions (User hovered out)
                        if (err.name === 'AbortError') return;
                        
                        // 3. Handle Autoplay Policy (Browser blocked sound)
                        if (err.name === 'NotAllowedError') {
                            // Check if we're still the active hover session
                            // If onMouseLeave ran, it would have removed/replaced this promise
                            if (playPromises.current[job.job_id] !== playSequence) return;

                            // Fallback to muted play
                            try {
                                video.muted = true;
                                await video.play();
                            } catch (mutedErr: any) {
                                if (mutedErr.name !== 'AbortError') {
                                    console.error("Muted play failed:", mutedErr);
                                }
                            }
                        } else {
                            console.error("Play failed:", err);
                        }
                      }
                    };
                    
                    playSequence = runSequence();
                    
                    // Track this specific sequence
                    playPromises.current[job.job_id] = playSequence;
                  }
                }
              }}
              onMouseLeave={() => {
                if (hasOutput) {
                  const video = videoRefs.current[job.job_id];
                  // 1. Mark current sequence as cancelled by removing it
                  delete playPromises.current[job.job_id];
                  
                  // 2. Immediately stop playback
                  if (video) {
                    video.pause();
                    video.currentTime = 0;
                    video.muted = true; // Reset to safe state
                  }
                }
              }}
              className={`break-inside-avoid relative overflow-hidden rounded-xl group mb-4 bg-gray-1600/20 ${
                hasOutput 
                  ? "cursor-pointer" 
                  : "cursor-not-allowed"
              }`}
            >
                {hasOutput ? (
                  <>
                    <video
                      ref={(el) => {
                        // Properly manage refs
                        if (el) {
                          videoRefs.current[job.job_id] = el;
                        } else {
                          delete videoRefs.current[job.job_id];
                        }
                      }}
                      key={job.output_url} // Force re-render if URL changes
                      src={job.output_url}
                      className="w-full h-auto object-contain transition-transform duration-300 group-hover:scale-105 bg-gray-1600/20"
                      style={{ display: 'block' }}
                      muted
                      loop
                      playsInline
                      preload="auto"
                      controls={false}
                      onError={(e) => {
                        console.error("Video load error:", e, "URL:", job.output_url, "Job:", job.job_id);
                        console.error("Video element:", e.currentTarget);
                        console.error("Error details:", e.currentTarget.error);
                      }}
                      onLoadedMetadata={(e) => {
                        // Seek to first frame to make it visible
                        try {
                          const video = e.currentTarget;
                          video.currentTime = 0.1;
                          // Request a frame update
                          requestAnimationFrame(() => {
                            video.currentTime = 0;
                          });
                        } catch (err) {
                          console.error("Error seeking video:", err);
                        }
                      }}
                      onLoadedData={(e) => {
                        // Ensure first frame is visible by seeking to start
                        try {
                          const video = e.currentTarget;
                          if (video.readyState >= 2 && video.paused) { // HAVE_CURRENT_DATA or higher, only if paused
                            video.currentTime = 0;
                          }
                        } catch (err) {
                          console.error("Error showing video frame:", err);
                        }
                      }}
                      onCanPlay={(e) => {
                        // Video is ready to play - seek to first frame to make it visible (only if paused)
                        try {
                          const video = e.currentTarget;
                          if (video.paused && video.currentTime !== 0) {
                            video.currentTime = 0;
                          }
                        } catch (err) {
                          // Ignore
                        }
                      }}
                    />
                    
                    {/* AI Model Label (Bottom Left - shown after video plays) */}
                    {(job.model_display_name || job.settings?.model_display_name) && (
                      <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-md border border-white/10 text-white text-[9px] font-medium px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                        {job.model_display_name || job.settings?.model_display_name}
                      </div>
                    )}

                    {/* Download Button (Top Right - Always Visible) */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        forceDownload(job.output_url, `video-${job.job_id.slice(0, 8)}.mp4`);
                      }}
                      className="absolute top-2 right-2 bg-black/40 backdrop-blur-md border border-white/10 text-white p-1.5 rounded-lg hover:bg-black/60 hover:border-white/20 transition-all z-20 shadow-lg"
                      title="Download Video"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                      </svg>
                    </button>
                  </>
                ) : isRunning ? (
                  <div className="relative w-full h-full overflow-hidden bg-gray-1600/20 flex items-center justify-center">
                    {/* Grey background with loading percentage */}
                    <p className="text-sm font-medium text-white">
                      {Math.round(loadingPercentages[job.job_id] || 0)}%
                    </p>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
        
        {/* Fade out overlay similar to ImageGallery */}
        {jobs.length > 12 && (
          <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-black-1100 via-black-1100/60 to-transparent pointer-events-none"></div>
        )}
      </div>
    </section>
  );
}
