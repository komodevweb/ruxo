"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import clsx from 'clsx'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/react'
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { getToken, apiClient } from "@/lib/api";
import VideoGallery from "@/app/components/VideoGallery";
import GalleryVideoCard from "@/app/components/GalleryVideoCard";
import { allImages } from "../../lib/gallery-images";

function page() {
     const { user, loading: authLoading } = useAuth();
     const router = useRouter();
     const [prompt, setPrompt] = useState("");
     const [negativePrompt, setNegativePrompt] = useState("");
     const [size, setSize] = useState("1280*720");
     const [duration, setDuration] = useState(5);
     const [audioFile, setAudioFile] = useState<File | null>(null);
     const [audioPreview, setAudioPreview] = useState<string | null>(null);
     const [audioUrl, setAudioUrl] = useState<string | null>(null);
     const [audioUploading, setAudioUploading] = useState(false);
     const [isGenerating, setIsGenerating] = useState(false);
     const isSubmittingRef = useRef(false);
     const [error, setError] = useState<string | null>(null);
     const [jobId, setJobId] = useState<string | null>(null);
     const [outputUrl, setOutputUrl] = useState<string | null>(null);
     const [jobStatus, setJobStatus] = useState<"pending" | "running" | "completed" | "failed" | null>(null);
     const [previousJobs, setPreviousJobs] = useState<any[]>([]);
     const [selectedJob, setSelectedJob] = useState<any | null>(null);
     const [isPolling, setIsPolling] = useState(false);
     const [rateLimited, setRateLimited] = useState(false);
     const [loadingJobs, setLoadingJobs] = useState(true);
     const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
     const [jobStartTime, setJobStartTime] = useState<number | null>(null);
     const [progress, setProgress] = useState(0);
     
     // Refs to track polling intervals for cleanup
     const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
     const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
     
     const audioInputRef = useRef<HTMLInputElement>(null);
     const audioDropRef = useRef<HTMLDivElement>(null);
     const [sidebarOpen, setSidebarOpen] = useState(false);
     const [isMobile, setIsMobile] = useState(false);

     // Lock body scroll when sidebar is open on mobile
     useEffect(() => {
          if (sidebarOpen) {
               document.body.style.overflow = 'hidden';
          } else {
               document.body.style.overflow = '';
          }
          return () => {
               document.body.style.overflow = '';
          };
     }, [sidebarOpen]);

     const [enablePromptExpansion, setEnablePromptExpansion] = useState(false);
     const [creditCache, setCreditCache] = useState<Map<string, number>>(new Map());
     const [models, setModels] = useState<any[]>([]);
     const [selectedModel, setSelectedModel] = useState<any>(null);
     const [loadingModels, setLoadingModels] = useState(true);
     
     // Aspect ratios for gallery variation
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

     // Safe localStorage helpers (handle cases where localStorage might not be available)
     const safeLocalStorage = {
          getItem: (key: string): string | null => {
               try {
                    if (typeof window !== 'undefined' && window.localStorage) {
                         return window.localStorage.getItem(key);
                    }
               } catch (error) {
                    console.warn("localStorage.getItem failed:", error);
               }
               return null;
          },
          setItem: (key: string, value: string): void => {
               try {
                    if (typeof window !== 'undefined' && window.localStorage) {
                         window.localStorage.setItem(key, value);
                    }
               } catch (error) {
                    console.warn("localStorage.setItem failed:", error);
               }
          },
          removeItem: (key: string): void => {
               try {
                    if (typeof window !== 'undefined' && window.localStorage) {
                         window.localStorage.removeItem(key);
                    }
               } catch (error) {
                    console.warn("localStorage.removeItem failed:", error);
               }
          }
     };
     
     // Ref-based credit cache for synchronous access without re-renders
     const creditCacheRef = useRef<Map<string, number>>(new Map());

     // Cleanup function to clear any active polling intervals
     const cleanupPolling = () => {
          console.log("🧹 Cleaning up polling intervals...");
          if (pollIntervalRef.current) {
               clearInterval(pollIntervalRef.current);
               pollIntervalRef.current = null;
               console.log("✅ Cleared poll interval");
          }
          if (pollTimeoutRef.current) {
               clearTimeout(pollTimeoutRef.current);
               pollTimeoutRef.current = null;
               console.log("✅ Cleared poll timeout");
          }
     };

     // Cleanup on component unmount
     useEffect(() => {
          return () => {
               cleanupPolling();
          };
     }, []);
     
     // Calculate progress based on elapsed time (slows down as it approaches 100%)
     useEffect(() => {
          if (!isGenerating || !jobStartTime || outputUrl) {
               if (outputUrl) {
                    setProgress(100);
               }
               return;
          }

          const updateProgress = () => {
               const now = Date.now();
               const elapsed = (now - jobStartTime) / 1000; // elapsed time in seconds
               
               // Estimate: typical video generation takes 60-180 seconds
               // Use a curve that slows down as it approaches 100%
               const estimatedTime = 120; // 2 minutes average
               const rawProgress = 100 * (1 - Math.exp(-elapsed / estimatedTime));
               
               // Cap at 95% until actually completed
               const cappedProgress = Math.min(rawProgress, 95);
               
               setProgress(Math.round(cappedProgress));
          };

          // Update immediately
          updateProgress();
          
          // Update every second
          const interval = setInterval(updateProgress, 1000);
          
          return () => clearInterval(interval);
     }, [isGenerating, jobStartTime, outputUrl]);

     // Initialize gallery images with aspect ratios
     const MAX_GALLERY_IMAGES = 12;
     const [galleryImages, setGalleryImages] = useState<Array<{ id: number; src: string; aspect: string }>>(() => {
          // Fixed initial state for SSR
          return allImages.slice(0, MAX_GALLERY_IMAGES).map((src, index) => ({
               id: index + 1,
               src,
               aspect: aspectRatios[index % aspectRatios.length],
          }));
     });

     useEffect(() => {
          // Shuffle images with random aspect ratios on mount - use requestIdleCallback for better performance
          const shuffleAndSetImages = () => {
               const shuffledImages = shuffleArray(allImages);
               const shuffled = shuffledImages.slice(0, MAX_GALLERY_IMAGES).map((src, index) => ({
                    id: index + 1,
                    src,
                    aspect: aspectRatios[index % aspectRatios.length],
               }));
               setGalleryImages(shuffled);
          };

          // Use requestIdleCallback if available, otherwise setTimeout
          if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
               requestIdleCallback(shuffleAndSetImages, { timeout: 1000 });
          } else {
               setTimeout(shuffleAndSetImages, 100);
          }
     }, []);

     // Resolution options with aspect ratios (will be filtered by model)
     const allResolutionOptions = [
          { label: "480p (Landscape)", value: "832*480" },
          { label: "480p (Portrait)", value: "480*832" },
          { label: "720p (Landscape)", value: "1280*720" },
          { label: "720p (Portrait)", value: "720*1280" },
          { label: "1080p (Landscape)", value: "1920*1080" },  // For other models
          { label: "1080p (Portrait)", value: "1080*1920" },  // For other models
          { label: "1080p (Landscape)", value: "1792*1024" },  // Sora 2 Pro specific
          { label: "1080p (Portrait)", value: "1024*1792" },  // Sora 2 Pro specific
     ];

     // Get available resolutions for selected model
     const getAvailableResolutions = () => {
          if (!selectedModel) return allResolutionOptions;
          return allResolutionOptions.filter(opt => 
               selectedModel.supported_resolutions.includes(opt.value)
          );
     };

     // Get available durations for selected model
     const getAvailableDurations = () => {
          if (!selectedModel) return [5, 10];
          return selectedModel.supported_durations;
     };

     useEffect(() => {
          const checkMobile = () => {
               setIsMobile(window.innerWidth < 1024);
          };
          checkMobile();
          window.addEventListener('resize', checkMobile);
          return () => window.removeEventListener('resize', checkMobile);
     }, []);

     // Cache keys for localStorage
     const MODELS_CACHE_KEY = 'ruxo_t2v_models_v2'; // Incremented version to bust cache
     const MODELS_CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours (matches backend Redis cache)
     const CREDITS_CACHE_KEY = 'ruxo_t2v_credits';
     const CREDITS_CACHE_TTL = 60 * 60 * 1000; // 1 hour (matches backend Redis cache)

     // Initialize credit cache from localStorage on mount
     useEffect(() => {
          if (typeof window !== 'undefined') {
               try {
                    const stored = localStorage.getItem(CREDITS_CACHE_KEY);
                    if (stored) {
                         const { data, timestamp } = JSON.parse(stored);
                         if (Date.now() - timestamp < CREDITS_CACHE_TTL) {
                              setCreditCache(new Map(Object.entries(data)));
                         } else {
                              localStorage.removeItem(CREDITS_CACHE_KEY);
                         }
                    }
               } catch (e) {
                    // Ignore localStorage errors
               }
          }
     }, []);

     // Persist credit cache to localStorage when it changes
     useEffect(() => {
          if (typeof window !== 'undefined' && creditCache.size > 0) {
               try {
                    const data = Object.fromEntries(creditCache);
                    localStorage.setItem(CREDITS_CACHE_KEY, JSON.stringify({
                         data,
                         timestamp: Date.now()
                    }));
               } catch (e) {
                    // Ignore localStorage errors
               }
          }
     }, [creditCache]);

     // Load available models on mount (with localStorage cache)
     useEffect(() => {
          loadModels();
     }, []);

     // Update size and duration when model changes
     useEffect(() => {
          if (selectedModel) {
               // Update to model's default resolution if current one is not supported
               if (!selectedModel.supported_resolutions.includes(size)) {
                    setSize(selectedModel.default_resolution);
               }
               // Update to model's default duration if current one is not supported
               if (!selectedModel.supported_durations.includes(duration)) {
                    setDuration(selectedModel.default_duration);
               }
          }
     }, [selectedModel]);

     // Pre-fetch credit costs for all available resolutions when model or duration changes
     useEffect(() => {
          if (selectedModel && duration && process.env.NEXT_PUBLIC_API_V1_URL) {
               const modelId = selectedModel.id || selectedModel.name;
               const availableResolutions = getAvailableResolutions();
               const availableDurations = getAvailableDurations();
               
               // Pre-fetch credits for all available resolutions and durations
               availableResolutions.forEach(opt => {
                    availableDurations.forEach((dur: number) => {
                         const cacheKey = `${modelId}-${opt.value}-${dur}`;
                         
                         // Only fetch if not already cached
                         if (!creditCache.has(cacheKey)) {
                              // getRequiredCredits already updates the cache internally
                              getRequiredCredits(opt.value, dur).catch((err) => {
                                   // Silently handle errors - don't spam console
                                   if (err instanceof TypeError && err.message === "Failed to fetch") {
                                        // Network error - expected in some cases
                                        return;
                                   }
                                   console.error("Error pre-fetching credits:", err);
                              });
                         }
                    });
               });
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [selectedModel, duration]);

     const loadModels = async () => {
          // Try localStorage cache first (models rarely change)
          if (typeof window !== 'undefined') {
               try {
                    const stored = localStorage.getItem(MODELS_CACHE_KEY);
                    if (stored) {
                         const { data, timestamp } = JSON.parse(stored);
                         if (Date.now() - timestamp < MODELS_CACHE_TTL && data.models?.length > 0) {
                              setModels(data.models);
                              setSelectedModel(data.models[0]);
                              setSize(data.models[0].default_resolution);
                              setDuration(data.models[0].default_duration);
                              setLoadingModels(false);
                              // Still refresh in background for freshness
                              fetchModelsFromAPI(true);
                              return;
                         }
                    }
               } catch (e) {
                    // Ignore cache errors, fetch from API
               }
          }
          
          await fetchModelsFromAPI(false);
     };

     const fetchModelsFromAPI = async (isBackgroundRefresh: boolean) => {
          try {
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/text-to-video/models`);
               const data = await response.json();
               
               if (response.ok && data.models) {
                    // Cache to localStorage
                    if (typeof window !== 'undefined') {
                         try {
                              localStorage.setItem(MODELS_CACHE_KEY, JSON.stringify({
                                   data,
                                   timestamp: Date.now()
                              }));
                         } catch (e) {
                              // Ignore localStorage errors
                         }
                    }
                    
                    setModels(data.models);
                    if (!isBackgroundRefresh && data.models.length > 0) {
                         setSelectedModel(data.models[0]);
                         setSize(data.models[0].default_resolution);
                         setDuration(data.models[0].default_duration);
                    }
               }
          } catch (err) {
               if (!isBackgroundRefresh) {
                    console.error("Error loading models:", err);
               }
          } finally {
               if (!isBackgroundRefresh) {
                    setLoadingModels(false);
               }
          }
     };

     // Fetch required credits from backend
     const getRequiredCredits = async (sizeValue: string, durationValue: number): Promise<number> => {
          if (!selectedModel) {
               // Fallback: return 0 if no model selected
               return 0;
          }
          
          const modelId = selectedModel.id || selectedModel.name;
          const cacheKey = `${modelId}-${sizeValue}-${durationValue}`;
          
          // Check ref cache first (synchronous, no re-render)
          if (creditCacheRef.current.has(cacheKey)) {
               return creditCacheRef.current.get(cacheKey)!;
          }
          
          // Check if API URL is available
          if (!process.env.NEXT_PUBLIC_API_V1_URL) {
               console.warn("API URL not configured");
               return 0;
          }
          
          try {
               const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_V1_URL}/text-to-video/calculate-credits?model_id=${encodeURIComponent(modelId)}&resolution=${encodeURIComponent(sizeValue)}&duration=${durationValue}`,
                    {
                         method: "GET",
                         headers: {
                              "Content-Type": "application/json",
                         },
                    }
               );
               
               if (response.ok) {
                    const data = await response.json();
                    const credits = data.credits || 0;
                    // Cache in ref (no re-render) AND state (for UI update)
                    creditCacheRef.current.set(cacheKey, credits);
                    setCreditCache(prev => {
                         const newCache = new Map(prev);
                         newCache.set(cacheKey, credits);
                         return newCache;
                    });
                    return credits;
          } else {
                    console.warn(`Failed to fetch credit cost: ${response.status} ${response.statusText}`);
               }
          } catch (error) {
               // Silently handle network errors - don't break the UI
               if (error instanceof TypeError && error.message === "Failed to fetch") {
                    // Network error - likely API is not available or CORS issue
                    console.warn("Network error fetching credit cost. API may be unavailable.");
               } else {
                    console.error("Error fetching credit cost:", error);
               }
          }
          
          // Fallback: return 0 on error
          return 0;
     };
     
     // Synchronous version for immediate display (uses ref cache to avoid re-renders)
     const getRequiredCreditsSync = (sizeValue: string, durationValue: number): number | undefined => {
          if (!selectedModel) {
               return 0;
          }
          
          const modelId = selectedModel.id || selectedModel.name;
          const cacheKey = `${modelId}-${sizeValue}-${durationValue}`;
          
          // Use ref for synchronous access (doesn't cause re-render)
          return creditCacheRef.current.get(cacheKey) ?? creditCache.get(cacheKey);
     };

     // Handle upgrade - redirect to pricing page
     const handleUpgrade = () => {
          router.push("/upgrade");
     };
     
     // Memoized callback for VideoGallery to prevent unnecessary re-renders
     const handleSelectJob = useCallback((job: any) => {
          setSelectedJob(job);
          
          // Auto-fill form for retrying failed jobs or reusing completed ones
          if (job) {
               // Restore prompt
               if (job.input_prompt || job.prompt) {
                    setPrompt(job.input_prompt || job.prompt);
               }
               
               // Restore settings
               if (job.settings || job) {
                    const settings = job.settings || job;
                    
                    if (settings.size) setSize(settings.size);
                    if (settings.duration) setDuration(settings.duration);
                    if (settings.negative_prompt) setNegativePrompt(settings.negative_prompt);
                    if (settings.enable_prompt_expansion !== undefined) {
                         setEnablePromptExpansion(settings.enable_prompt_expansion);
                    }
                    
                    // Restore model if available in list
                    if ((settings.model || settings.model_id) && models.length > 0) {
                         const modelId = settings.model || settings.model_id;
                         const model = models.find(m => m.id === modelId);
                         if (model) setSelectedModel(model);
                    }
               }
               
               // If on mobile, open sidebar so user sees the populated form
               if (window.innerWidth < 1024) {
                    setSidebarOpen(true);
               }
               
               // If it was a failed job, scroll to top/sidebar on desktop too? 
               // Optional but good UX
          }
     }, [models]);

     // Get button text and action
     const getButtonConfig = () => {
          if (isGenerating) return { text: "Generating...", action: handleGenerate };
          if (audioUploading) return { text: "Uploading...", action: handleGenerate };
          
          if (!user) return { text: "Generate", action: () => router.push("/signup") };
          
          const hasSubscription = !!user.plan_name;
          const creditsValue = getRequiredCreditsSync(size, duration);
          const requiredCredits = creditsValue ?? 0; // Fallback for logic
          const hasEnoughCredits = (user.credit_balance || 0) >= requiredCredits;
          
          if (!hasEnoughCredits) {
               return { text: "Get More Credits", action: () => router.push("/upgrade") };
          }
          
          return { 
               text: creditsValue !== undefined ? `Generate (${creditsValue})` : "Generate (...)", 
               action: handleGenerate 
          };
     };

     // Load previous jobs on mount
     useEffect(() => {
          // Wait for auth to finish loading before deciding what to show
          if (authLoading) {
               // Auth is still loading, keep shimmer showing
               setLoadingJobs(true);
               setHasLoadedOnce(false);
               return;
          }
          
          // Auth has finished loading, now we can decide
          if (user) {
               // User is logged in, keep loading state true until we load jobs
               setLoadingJobs(true);
               setHasLoadedOnce(false);
               loadPreviousJobs();
          } else {
               // User is not logged in - set all states together in one batch
               // This prevents any flicker between states
               setPreviousJobs([]);
               setLoadingJobs(false);
               setHasLoadedOnce(true);
          }
     }, [user, authLoading]);

     // Auto-refresh jobs list periodically
     useEffect(() => {
          if (!user) return;

          const jobsPollInterval = setInterval(() => {
               if (!rateLimited) {
                    loadPreviousJobs();
               }
          }, 15000);

          return () => clearInterval(jobsPollInterval);
     }, [user, rateLimited]);

     // Ref to track previous jobs for comparison (avoid unnecessary re-renders)
     const previousJobsRef = useRef<string>("");
     
     const loadPreviousJobs = async () => {
          const token = getToken();
          if (!token) {
               setPreviousJobs([]);
               setLoadingJobs(false);
               setHasLoadedOnce(true);
               return;
          }

          try {
               // Don't set loading here - it's already set in useEffect
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/text-to-video/all-jobs?limit=100`, {
                    headers: {
                         "Authorization": `Bearer ${token}`
                    }
               });

               if (response.status === 429) {
                    console.warn("Rate limit exceeded, pausing auto-refresh for 60 seconds");
                    setRateLimited(true);
                    setLoadingJobs(false); // Stop loading even on rate limit
                    setTimeout(() => {
                         setRateLimited(false);
                    }, 60000);
                    return;
               }

               const data = await response.json();

               if (response.ok && data.jobs) {
                    // IMPORTANT: Only update state if jobs data actually changed
                    // This prevents unnecessary re-renders that cause blinking
                    const newJobsKey = data.jobs.map((j: any) => `${j.job_id}:${j.status}:${j.output_url || ''}`).join('|');
                    
                    if (newJobsKey !== previousJobsRef.current) {
                         previousJobsRef.current = newJobsKey;
                         setPreviousJobs(data.jobs);
                    }
                    
                    // Always update loading state (but only once per mount)
                    if (loadingJobs || !hasLoadedOnce) {
                         setLoadingJobs(false);
                         setHasLoadedOnce(true);
                    }
                    
                    // Check for any pending/running jobs and automatically resume generation state
                    const runningJob = data.jobs.find((job: any) => 
                         (job.status === "pending" || job.status === "running" || job.status === "processing") && !job.output_url
                    );
                    
                    if (runningJob) {
                         // Automatically resume generating state for running job
                         const runningJobId = runningJob.job_id;
                         
                         // Set job ID if not already set
                         if (!jobId) {
                              setJobId(runningJobId);
                         }
                         
                         // Restore job start time from localStorage or use creation time
                         if (!jobStartTime && runningJob.created_at) {
                              const storedStartTime = safeLocalStorage.getItem(`job_start_${runningJobId}`);
                              if (storedStartTime) {
                                   setJobStartTime(parseInt(storedStartTime));
                              } else {
                                   // Use job creation time as fallback
                                   const createdTime = new Date(runningJob.created_at).getTime();
                                   setJobStartTime(createdTime);
                                   safeLocalStorage.setItem(`job_start_${runningJobId}`, createdTime.toString());
                              }
                         }
                         
                         // Resume generating state and polling
                         if (!isGenerating) {
                              setIsGenerating(true);
                         }
                         if (!isPolling && !pollIntervalRef.current) {
                              console.log("🔄 Resuming polling for running job:", runningJobId);
                              setIsPolling(true);
                              pollJobStatus(runningJobId);
                         }
                    } else if (data.jobs.length > 0 && !selectedJob && !outputUrl && !isGenerating && !isPolling && !jobId) {
                         // If no running job, no selection, and we're in initial state, check for recent completed job
                         const mostRecentJob = data.jobs[0];
                         const jobTime = new Date(mostRecentJob.created_at).getTime();
                         const now = Date.now();
                         
                         // Only auto-select if created within last 5 minutes
                         if (now - jobTime < 5 * 60 * 1000) {
                              console.log("🔄 Auto-selecting recent job:", mostRecentJob.job_id);
                              if (mostRecentJob.status === "completed" && mostRecentJob.output_url) {
                                   setOutputUrl(mostRecentJob.output_url);
                                   setSelectedJob(mostRecentJob);
                                   setJobStatus("completed");
                              } else if (mostRecentJob.status === "failed") {
                                   setSelectedJob(mostRecentJob);
                                   setJobStatus("failed");
                                   setError(mostRecentJob.error || "Generation failed");
                              }
                         }
                    } else if (jobId) {
                         // Check specific job if jobId is set
                         const currentJob = data.jobs.find((job: any) => job.job_id === jobId);
                         if (currentJob) {
                              // Restore job start time from localStorage if not set
                              if (!jobStartTime && currentJob.created_at) {
                                   const storedStartTime = safeLocalStorage.getItem(`job_start_${jobId}`);
                                   if (storedStartTime) {
                                        setJobStartTime(parseInt(storedStartTime));
                                   } else {
                                        // Use job creation time as fallback
                                        const createdTime = new Date(currentJob.created_at).getTime();
                                        setJobStartTime(createdTime);
                                        safeLocalStorage.setItem(`job_start_${jobId}`, createdTime.toString());
                                   }
                              }
                              
                              if ((currentJob.status === "pending" || currentJob.status === "running" || currentJob.status === "processing") && !currentJob.output_url) {
                                   // Resume generating state and polling only if not already generating
                                   if (!isGenerating) {
                                        setIsGenerating(true);
                                   }
                                   if (!isPolling && !pollIntervalRef.current) {
                                        console.log("🔄 Resuming polling for job:", jobId);
                                        setIsPolling(true);
                                        pollJobStatus(jobId);
                                   }
                              } else if (currentJob.status === "completed" && currentJob.output_url) {
                                   // Job completed, stop generating
                                   setOutputUrl(currentJob.output_url);
                                   setJobStatus("completed");
                                   setProgress(100);
                                   setIsGenerating(false);
                                   setIsPolling(false);
                                   isSubmittingRef.current = false; // Reset ref
                                   cleanupPolling();
                                   // Clean up localStorage
                                   safeLocalStorage.removeItem(`job_start_${jobId}`);
                              } else if (currentJob.status === "failed") {
                                   // Job failed
                                   setError(currentJob.error || "Video generation failed. Please try changing your prompt.");
                                   setIsGenerating(false);
                                   setIsPolling(false);
                                   isSubmittingRef.current = false; // Reset ref
                                   cleanupPolling();
                                   // Clean up localStorage
                                   safeLocalStorage.removeItem(`job_start_${jobId}`);
                              }
                         }
                    }
                    
                    if (selectedJob) {
                         const updatedSelectedJob = data.jobs.find((job: any) => job.job_id === selectedJob.job_id);
                         if (updatedSelectedJob) {
                              // Only update if something changed
                              if (updatedSelectedJob.status !== selectedJob.status || 
                                  updatedSelectedJob.output_url !== selectedJob.output_url) {
                                   setSelectedJob(updatedSelectedJob);
                                   if (updatedSelectedJob.status === "completed" && updatedSelectedJob.output_url) {
                                        setOutputUrl(updatedSelectedJob.output_url);
                                        setJobStatus("completed");
                                   }
                              }
                         }
                    }
               } else {
                    // If response is not ok or no jobs, set empty array and stop loading
                    if (previousJobs.length > 0) {
                         setPreviousJobs([]);
                         previousJobsRef.current = "";
                    }
                    setLoadingJobs(false);
                    setHasLoadedOnce(true);
               }
          } catch (err) {
               console.error("Error loading previous jobs:", err);
               if (previousJobs.length > 0) {
                    setPreviousJobs([]);
                    previousJobsRef.current = "";
               }
               setLoadingJobs(false);
               setHasLoadedOnce(true);
          }
     };

     const uploadFileToBackblaze = async (file: File) => {
          const token = getToken();
          if (!token) {
               router.push("/login");
               return null;
          }

          const formData = new FormData();
          formData.append("file", file);

          try {
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/storage/upload/text-to-video`, {
                    method: "POST",
                    headers: {
                         "Authorization": `Bearer ${token}`
                    },
                    body: formData
               });

               const data = await response.json();

               if (!response.ok) {
                    throw new Error(data.detail || "Failed to upload file");
               }

               return data.url;
          } catch (err: any) {
               console.error("Error uploading audio:", err);
               setError(`Failed to upload audio: ${err.message}`);
               return null;
          }
     };

     const handleAudioSelect = async (file: File) => {
          if (!file.type.startsWith("audio/")) {
               setError("Please select an audio file (WAV or MP3)");
               return;
          }

          // Check file size (15 MB limit)
          if (file.size > 15 * 1024 * 1024) {
               setError("Audio file must be 15 MB or less");
               return;
          }

          setAudioFile(file);
          setAudioUploading(true);
          setError(null);

          // Create preview
          const reader = new FileReader();
          reader.onload = (e) => {
               setAudioPreview(e.target?.result as string);
          };
          reader.readAsDataURL(file);

          // Upload to Backblaze immediately
          const url = await uploadFileToBackblaze(file);
          if (url) {
               setAudioUrl(url);
               console.log("Audio uploaded to Backblaze:", url);
          }
          setAudioUploading(false);
     };

     const handleGenerate = async () => {
          // Prevent double submission with both state and ref check
          if (isGenerating || isSubmittingRef.current) {
               return;
          }

          if (!user) {
               router.push("/login");
               return;
          }

          if (!prompt.trim()) {
               setError("Please enter a prompt");
               return;
          }

          // CRITICAL: Clean up any existing polling intervals before starting new generation
          console.log("🔄 Starting new generation - cleaning up old polling intervals");
          cleanupPolling();
          setIsPolling(false);
          
          // Set ref immediately to prevent double submission
          isSubmittingRef.current = true;
          setIsGenerating(true);
          setError(null);
          setOutputUrl(null);
          setJobStatus(null);

          try {
               const token = getToken();
               if (!token) {
                    router.push("/login");
                    return;
               }

               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/text-to-video/submit`, {
                    method: "POST",
                    headers: {
                         "Authorization": `Bearer ${token}`,
                         "Content-Type": "application/json"
                    },
                    credentials: "include",
                    body: JSON.stringify({
                         prompt: prompt,
                         model: selectedModel?.id || "google-veo-3.1",
                         size: size,
                         duration: duration,
                         negative_prompt: negativePrompt || undefined,
                         audio_url: audioUrl || undefined,
                         enable_prompt_expansion: enablePromptExpansion,
                         seed: -1
                    })
               });

               const data = await response.json();

               if (!response.ok) {
                    if (response.status === 401) {
                         setError("Your session has expired. Please log in again.");
                         setTimeout(() => {
                              router.push("/login");
                         }, 2000);
                         return;
                    }
                    throw new Error(data.detail || "Failed to submit job");
               }

               console.log("Job submitted:", data);
               setJobId(data.job_id);
               setJobStatus("pending");
               
               // Store job start time for progress calculation (persists across refreshes)
               const startTime = Date.now();
               setJobStartTime(startTime);
               if (data.job_id) {
                    safeLocalStorage.setItem(`job_start_${data.job_id}`, startTime.toString());
               }
               
               setIsPolling(true);
               loadPreviousJobs();
               pollJobStatus(data.job_id);

          } catch (err: any) {
               console.error("Error submitting job:", err);
               setError(err.message || "Failed to submit job. Please try again.");
               setIsGenerating(false);
               isSubmittingRef.current = false; // Reset ref on error
          }
     };

     const pollJobStatus = async (jobIdToPoll: string) => {
          const token = getToken();
          if (!token) {
               setIsGenerating(false);
               return;
          }

          // Check if polling is already active
          if (pollIntervalRef.current || pollTimeoutRef.current) {
               console.warn("⚠️ Polling already active, cleaning up before starting new poll");
               cleanupPolling();
          }

          const MAX_POLL_TIME = 10 * 60 * 1000; // 10 minutes total
          const POLL_INTERVAL = 3000; // 3 seconds
          const REQUEST_TIMEOUT = 10000; // 10 seconds per request

          const poll = async () => {
               const abortController = new AbortController();
               const requestTimeout = setTimeout(() => abortController.abort(), REQUEST_TIMEOUT);

               try {
                    const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/text-to-video/status/${jobIdToPoll}`, {
                         headers: {
                              "Authorization": `Bearer ${token}`
                         },
                         signal: abortController.signal
                    });

                    clearTimeout(requestTimeout);
                    const data = await response.json();

                    if (response.ok && data) {
                         setJobStatus(data.status);

                         if (data.status === "completed" && data.output_url) {
                              setOutputUrl(data.output_url);
                              setProgress(100);
                              setIsGenerating(false);
                              setIsPolling(false);
                              isSubmittingRef.current = false;
                              cleanupPolling();
                              // Clean up localStorage
                              if (jobIdToPoll) {
                                   safeLocalStorage.removeItem(`job_start_${jobIdToPoll}`);
                              }
                              loadPreviousJobs();
                         } else if (data.status === "failed") {
                              setError(data.error || "Video generation failed. Please try changing your prompt.");
                              setIsGenerating(false);
                              setIsPolling(false);
                              isSubmittingRef.current = false;
                              cleanupPolling();
                              // Clean up localStorage
                              if (jobIdToPoll) {
                                   safeLocalStorage.removeItem(`job_start_${jobIdToPoll}`);
                              }
                         } else if (data.status === "running" || data.status === "pending") {
                              setJobStatus(data.status);
                         }
                    }
               } catch (err: any) {
                    clearTimeout(requestTimeout);
                    if (err.name === 'AbortError') {
                         console.warn("Request timeout during polling, will retry on next poll");
                    } else {
                         console.error("Error polling job status:", err);
                    }
               }
          };

          // Poll immediately, then every 3 seconds
          poll();
          pollIntervalRef.current = setInterval(poll, POLL_INTERVAL);
          console.log("✅ Started polling interval:", pollIntervalRef.current);

          // Overall timeout after 10 minutes
          pollTimeoutRef.current = setTimeout(() => {
               cleanupPolling();
               const currentStatus = jobStatus;
               if (currentStatus !== "completed" && currentStatus !== "failed") {
                    // Don't set error, just stop blocking the UI
                    // The job continues in background and will appear in gallery when done
                    setIsGenerating(false);
                    setIsPolling(false);
                    isSubmittingRef.current = false;
                    
                    // Optional: Show a toast or smaller notification instead of error
                    console.log("Polling timeout reached - job continues in background");
                    
                    // Clean up localStorage so we don't auto-resume this specific job immediately
                    if (jobIdToPoll) {
                         safeLocalStorage.removeItem(`job_start_${jobIdToPoll}`);
                    }
               }
          }, MAX_POLL_TIME);
          console.log("✅ Started polling timeout:", pollTimeoutRef.current);
     };

     return (
          <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
               <style jsx global>{`
                    .no-scrollbar::-webkit-scrollbar {
                         display: none;
                    }
                    .no-scrollbar {
                         -ms-overflow-style: none;
                         scrollbar-width: none;
                    }
               `}</style>
               <section className="">
                    <div className={`fixed z-[999] 
    ${sidebarOpen ? "left-0" : "-left-full"} 
    md:left-0 md:top-[72px] top-0 md:w-[301px] w-full flex flex-col justify-between 
    md:h-[calc(100vh_-_72px)] h-screen md:bottom-auto bottom-0 
    border-r border-gray-1300 md:py-8 pt-[120px] px-4 sidebar-bg
    transition-all duration-300 overflow-y-auto scroll-smooth
    md:pb-8 pb-20
   `} style={{ paddingBottom: 'max(5rem, calc(1rem + env(safe-area-inset-bottom, 0px)))' }}>
                         {/* Mobile-only close button */}
                         <button
                              onClick={() => setSidebarOpen(false)}
                              className="md:hidden absolute top-[90px] right-4 w-8 h-8 flex items-center justify-center text-white/80 hover:text-white transition-colors z-[1001]"
                              aria-label="Close sidebar"
                         >
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                   <line x1="18" y1="6" x2="6" y2="18"></line>
                                   <line x1="6" y1="6" x2="18" y2="18"></line>
                              </svg>
                         </button>
                         <div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Prompt</h3>
                                   <textarea
                                        className="w-full h-32 rounded-lg border border-gray-1100 bg-black-1000 p-3 text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                        placeholder="Describe the video you want to generate..."
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                   />
                              </div>
                              <div className="mb-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Model</h3>
                                   {loadingModels ? (
                                        <div className="relative w-full rounded-lg bg-gray-1600 py-2 px-3 overflow-hidden">
                                             <div className="h-5 bg-gray-1200/30 rounded"></div>
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : selectedModel ? (
                                        <Listbox value={selectedModel} onChange={setSelectedModel}>
                                             <ListboxButton
                                                  className={clsx(
                                                       'relative flex items-center justify-between w-full rounded-lg bg-gray-1600 py-2 px-3 text-left text-sm/6 text-white',
                                                       'focus:outline-none data-[focus]:outline-2 data-[focus]:-outline-offset-2 data-[focus]:outline-white/25'
                                                  )}
                                             >
                                                  <div className="flex items-center gap-2">
                                                       <img src={selectedModel.icon} alt="" className="w-4 h-4" />
                                                       <span className="block truncate text-sm font-medium">{selectedModel.name || selectedModel.display_name}</span>
                                                  </div>
                                                  <img src="/images/droparrow.svg" alt="" className="w-2.5 h-2.5 opacity-60" />
                                             </ListboxButton>

                                             <ListboxOptions
                                                  anchor={isMobile ? "bottom start" : "right start"}
                                                  transition
                                                  className={clsx(
                                                       'w-[var(--button-width)] lg:w-[300px] rounded-xl border border-white/5 bg-[#1A1D24] p-1 focus:outline-none z-[9999]',
                                                       !isMobile && 'lg:ml-2',
                                                       'transition duration-100 ease-in data-[leave]:data-[closed]:opacity-0'
                                                  )}
                                             >
                                                  {models.map((model) => (
                                                       <ListboxOption
                                                            key={model.id}
                                                            value={model}
                                                            className="group flex cursor-default items-center gap-3 rounded-lg py-2 px-3 select-none data-[focus]:bg-white/10"
                                                       >
                                                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/5">
                                                                 <img src={model.icon} alt="" className="w-5 h-5" />
                                                            </div>
                                                            <div className="flex flex-col">
                                                                 <div className="flex items-center gap-2">
                                                                      <span className="text-sm font-medium text-white">{model.name || model.display_name}</span>
                                                                 </div>
                                                                 <span className="text-[10px] text-white/50 line-clamp-1">{model.description}</span>
                                                            </div>
                                                       </ListboxOption>
                                                  ))}
                                             </ListboxOptions>
                                        </Listbox>
                                   ) : null}
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Resolution</h3>
                                   <div className="grid grid-cols-1 gap-1">
                                        {getAvailableResolutions().map((opt) => {
                                             const credits = getRequiredCreditsSync(opt.value, duration);
                                             return (
                                                  <button
                                                       key={opt.value}
                                                       type="button"
                                                       onClick={() => setSize(opt.value)}
                                                       className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-between px-3 w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
            ${size === opt.value ? "bg-gray-1100/30! border-blue-1100!" : ""} 
          `}
                                                  >
                                                       <span>{opt.label}</span>
                                                       <span className="text-white/60">
                                                            {credits !== undefined ? `(${credits})` : <span className="animate-pulse">...</span>}
                                                       </span>
                                                  </button>
                                             );
                                        })}
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Duration</h3>
                                   <div className="grid grid-cols-2 gap-1">
                                        {getAvailableDurations().map((dur: number) => (
                                             <button
                                                  key={dur}
                                                  type="button"
                                                  onClick={() => setDuration(dur)}
                                                  className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
                                                            ${duration === dur ? "bg-gray-1100/30! border-blue-1100!" : ""} 
                                                       `}
                                             >
                                                  {dur}s
                                             </button>
                                        ))}
                                   </div>
                              </div>
                              {selectedModel?.supports_negative_prompt && (
                                   <div className="mb-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Negative Prompt (Optional)</h3>
                                        <textarea
                                             className="w-full h-24 rounded-lg border border-gray-1100 bg-black-1000 p-3 text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                             placeholder="What you don't want in the video..."
                                             value={negativePrompt}
                                             onChange={(e) => setNegativePrompt(e.target.value)}
                                        />
                                   </div>
                              )}
                              {selectedModel?.supports_audio && (
                                   <div className="mb-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Audio (Optional)</h3>
                                   <input
                                        type="file"
                                        ref={audioInputRef}
                                        accept="audio/wav,audio/mp3,audio/*"
                                        className="hidden"
                                        onChange={(e) => {
                                             const file = e.target.files?.[0];
                                             if (file) {
                                                  handleAudioSelect(file);
                                             }
                                        }}
                                   />
                                   <div 
                                        ref={audioDropRef}
                                        onClick={() => audioInputRef.current?.click()}
                                        onDragOver={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (audioDropRef.current) {
                                                  audioDropRef.current.classList.add("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDragLeave={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (audioDropRef.current) {
                                                  audioDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDrop={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (audioDropRef.current) {
                                                  audioDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                             const file = e.dataTransfer.files[0];
                                             if (file && file.type.startsWith("audio/")) {
                                                  handleAudioSelect(file);
                                             } else {
                                                  setError("Please drop an audio file");
                                             }
                                        }}
                                        className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-4 text-center cursor-pointer hover:border-blue-1100 transition-colors relative"
                                   >
                                        {audioUploading && (
                                             <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center z-20">
                                                  <div className="text-xs text-white">Uploading...</div>
                                             </div>
                                        )}
                                        {audioUrl ? (
                                             <div className="text-[10px] text-green-400">✓ Audio uploaded</div>
                                        ) : (
                                             <>
                                                  <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400 mb-2">
                                                       <img src="/images/play-icon.svg" alt="" />
                                                  </div>
                                                  <h6 className="text-xs font-medium leading-[120%] text-white mb-1">Upload Audio</h6>
                                                  <p className="text-[10px] text-white/60">WAV/MP3, 3-30s, ≤15MB</p>
                                                  <p className="text-[10px] text-white/40 mt-1">or drag and drop</p>
                                             </>
                                        )}
                                   </div>
                              </div>
                              )}
                              {selectedModel?.supports_prompt_expansion && (
                                   <div className="mb-6">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                             <input
                                                  type="checkbox"
                                                  checked={enablePromptExpansion}
                                                  onChange={(e) => setEnablePromptExpansion(e.target.checked)}
                                                  className="w-4 h-4 rounded border-gray-1100 bg-black-1000 text-blue-1100 focus:ring-blue-1100"
                                             />
                                             <span className="text-xs text-white/60">Enable Prompt Expansion</span>
                                        </label>
                                   </div>
                              )}
                         </div>
                         <div className="text-center lg:pb-0" style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom, 0px))' }}>
                              {error && (
                                   <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg">
                                        <p className="text-xs text-red-400">{error}</p>
                                   </div>
                              )}
                              {(() => {
                                   const buttonConfig = getButtonConfig();
                                   const isGenerateAction = buttonConfig.action === handleGenerate;
                                   // Only disable if generating/uploading, OR if prompt is empty/invalid when trying to generate
                                   const isDisabled = isGenerateAction && (isGenerating || audioUploading || isSubmittingRef.current || !prompt.trim());
                                   const isLoading = isGenerating || audioUploading;
                                   
                                   return (
                                        <button 
                                             onClick={(e) => {
                                                  e.preventDefault();
                                                  e.stopPropagation();
                                                  if (!isGenerating && !audioUploading && !isSubmittingRef.current) {
                                                       buttonConfig.action();
                                                  }
                                             }}
                                             disabled={isDisabled}
                                             className={clsx(
                                                  "md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-flex items-center justify-center gap-2 py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl transition-all duration-300 relative overflow-hidden",
                                                  isDisabled 
                                                       ? "cursor-not-allowed" 
                                                       : "hover:shadow-7xl"
                                             )} 
                                        >
                                             {isLoading && (
                                                  <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                                             )}
                                             {buttonConfig.text}
                                        </button>
                                   );
                              })()}
                         </div>
                    </div>
                    <div className={`md:w-[calc(100%_-_301px)] px-5 flex flex-col ml-auto ${
                         !loadingJobs && previousJobs.length > 0
                              ? "items-start justify-start pt-[72px] pb-10 min-h-screen" 
                              : "items-center justify-center flex-col md:pt-[160px] pt-[110px] py-20 min-h-screen"
                    }`}>
                         {loadingJobs || !hasLoadedOnce || authLoading ? (
                              <div className="w-full max-w-[1320px] mx-auto">
                                   <VideoGallery 
                                        jobs={[]}
                                        selectedJobId={selectedJob?.job_id}
                                        loading={true}
                                        onSelectJob={handleSelectJob}
                                   />
                              </div>
                         ) : previousJobs.length > 0 ? (
                              <div className="w-full max-w-[1320px] mx-auto">
                                   <div className="md:hidden block mb-6 px-5" style={{ paddingBottom: 'max(1.5rem, calc(1.5rem + env(safe-area-inset-bottom, 0px)))' }}>
                                        <div className="text-center mb-6">
                                             <div className="flex gap-2 items-center justify-center mb-2">
                                                  <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">NEW</span>
                                                  <h6 className="text-sm font-normal leading-[120%] text-gradient">Text to Video</h6>
                                             </div>
                                             <h2 className="text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Turn Text Into Video</h2>
                                             <p className="text-sm font-medium leading-[120%] text-white/60 mb-6">Turn text into high-impact creative videos powered by the latest AI models.</p>
                                             <button 
                                                  onClick={() => setSidebarOpen(true)} 
                                                  className="text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300" 
                                             >
                                                  Generate
                                             </button>
                                        </div>
                                   </div>
                                   <VideoGallery 
                                        jobs={previousJobs}
                                        selectedJobId={selectedJob?.job_id}
                                        loading={false}
                                        onSelectJob={handleSelectJob}
                                   />
                              </div>
                         ) : (
                              <>
                                   <div className="text-center mb-6 pt-4 md:pt-0">
                                        <div className="flex gap-2 items-center justify-center">
                                             <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">NEW</span>
                                             <h6 className="text-sm font-normal leading-[120%] text-gradient">Text to Video</h6>
                                        </div>
                                        <h2 className="md:text-5xl text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Turn Text Into Video</h2>
                                        <p className="md:text-base text-sm font-medium leading-[120%] text-white/60">Turn text into high-impact creative videos powered by the latest AI models.</p>
                                        <div className="md:hidden block mt-12" style={{ paddingBottom: 'max(1.5rem, calc(1.5rem + env(safe-area-inset-bottom, 0px)))' }}>
                                             <button 
                                                  onClick={() => setSidebarOpen(true)} 
                                                  className="md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300" 
                                             >
                                                  Generate
                                             </button>
                                        </div>
                                   </div>
                                   {/* Photo Gallery */}
                                   <div className="w-full max-w-[1320px] mx-auto px-5 mt-12 pb-20">
                                        {/* Featured Videos */}
                                        <div className="mb-16">
                                             <div className="flex items-center justify-between mb-6">
                                                  <h3 className="text-xl font-medium text-white flex items-center gap-2">
                                                       Featured Generations
                                                  </h3>
                                             </div>
                                             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                  {["/images/upgrade/1128_1.mp4?v=1", "/images/upgrade/1128_2.mp4?v=1", "/images/upgrade/1128_3.mp4?v=1", "/images/upgrade/1128_4.mp4?v=1"].map((src, i) => (
                                                       <GalleryVideoCard key={i} src={src} aspectRatio="aspect-[9/16]" />
                                                  ))}
                                             </div>
                                        </div>

                                        {/* Community Showcase */}
                                        <div>
                                             <div className="flex items-center justify-between mb-6">
                                                  <h3 className="text-xl font-medium text-white flex items-center gap-2">
                                                       Community Showcase
                                                  </h3>
                                             </div>
                                             <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
                                                  {galleryImages.map((img, idx) => (
                                                       <div key={`${img.id}-${idx}`} className={`break-inside-avoid relative group rounded-2xl overflow-hidden bg-[#1A1D24] border border-white/5 ${img.aspect} hover:border-white/20 transition-colors duration-300`}>
                                                            <img 
                                                                 src={img.src} 
                                                                 alt="" 
                                                                 className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                                                                 loading={idx < 4 ? "eager" : "lazy"}
                                                                 decoding="async"
                                                            />
                                                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                                                                 <div className="w-full">
                                                                      <div className="flex items-center justify-between">
                                                                           <span className="text-[10px] font-medium text-white/90 bg-white/10 backdrop-blur-md border border-white/10 px-2.5 py-1 rounded-full">Remix</span>
                                                                           <div className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center transform translate-y-2 group-hover:translate-y-0 opacity-0 group-hover:opacity-100 transition-all duration-300 delay-75">
                                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                                                                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                                </svg>
                                                                           </div>
                                                                      </div>
                                                                 </div>
                                                            </div>
                                                       </div>
                                                  ))}
                                             </div>
                                        </div>
                                   </div>
                              </>
                         )}
                         
                         {/* Generating indicator - shows on both pages */}
                         {isGenerating && !outputUrl && (
                              <div className="fixed bottom-8 right-8 z-50 bg-black-1000 border border-gray-1100 p-4 rounded-xl shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom-4">
                                   <div className="w-12 h-12 rounded-lg overflow-hidden relative">
                                        <div className="w-full h-full bg-gray-1100 flex items-center justify-center">
                                             <div className="w-6 h-6 border-2 border-blue-1100 border-t-transparent rounded-full animate-spin"></div>
                                        </div>
                                   </div>
                                   <div>
                                        <h4 className="text-sm font-medium text-white">Generating Video...</h4>
                                        <p className="text-xs text-white/60">This may take a few minutes</p>
                                   </div>
                              </div>
                         )}
                    </div>
               </section>
          </div>
     )
}

export default page
