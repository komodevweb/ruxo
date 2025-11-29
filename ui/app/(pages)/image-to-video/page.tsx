"use client";
import { useState, useRef, useEffect } from "react";
import clsx from 'clsx'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/react'
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { getToken, apiClient } from "@/lib/api";
import VideoGallery from "@/app/components/VideoGallery";
import GalleryVideoCard from "@/app/components/GalleryVideoCard";
import { allImages } from "../../lib/gallery-images";

function Page() {
     const { user, loading: authLoading } = useAuth();
     const router = useRouter();
     const [prompt, setPrompt] = useState("");
     const [negativePrompt, setNegativePrompt] = useState("");
     const [size, setSize] = useState("720p");
     const [duration, setDuration] = useState(5);
     const [imageFile, setImageFile] = useState<File | null>(null);
     const [imagePreview, setImagePreview] = useState<string | null>(null);
     const [imageUrl, setImageUrl] = useState<string | null>(null);
     const imageUrlRef = useRef<string | null>(null); // Ref to track current image URL
     const uploadTimestampRef = useRef<number>(0); // Track when image was uploaded to ensure we use latest
     
     // Refs to track polling intervals for cleanup
     const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
     const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
     
     // Keep ref in sync with state to ensure we always have the latest URL
     useEffect(() => {
          imageUrlRef.current = imageUrl;
          if (imageUrl) {
               console.log("🔄 Image URL ref synced with state:", imageUrl);
          }
     }, [imageUrl]);
     const [imageUploading, setImageUploading] = useState(false);
     const [audioFile, setAudioFile] = useState<File | null>(null);
     const [audioPreview, setAudioPreview] = useState<string | null>(null);
     const [audioUrl, setAudioUrl] = useState<string | null>(null);
     const [audioUploading, setAudioUploading] = useState(false);
     const [enablePromptExpansion, setEnablePromptExpansion] = useState(false);
     const [aspectRatio, setAspectRatio] = useState<string>("16:9");
     const [creditCache, setCreditCache] = useState<Map<string, number>>(new Map());
     const [isGenerating, setIsGenerating] = useState(false);
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
     const isSubmittingRef = useRef(false);
     const imageInputRef = useRef<HTMLInputElement>(null);
     const imageDropRef = useRef<HTMLDivElement>(null);
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

     // Initialize gallery images with aspect ratios
     const MAX_GALLERY_IMAGES = 12;
     const [galleryImages, setGalleryImages] = useState<Array<{ id: number; src: string; aspect: string }>>(() => {
          // Fixed initial state for SSR
          try {
               const images = Array.isArray(allImages) && allImages.length > 0 
                    ? allImages 
                    : [];
               return images.slice(0, MAX_GALLERY_IMAGES).map((src, index) => ({
                    id: index + 1,
                    src,
                    aspect: aspectRatios[index % aspectRatios.length],
               }));
          } catch (error) {
               console.error("Error initializing gallery images:", error);
               return [];
          }
     });

     useEffect(() => {
          // Shuffle images with random aspect ratios on mount - use requestIdleCallback for better performance
          const shuffleAndSetImages = () => {
               try {
                    const images = Array.isArray(allImages) && allImages.length > 0 
                         ? allImages 
                         : [];
                    if (images.length === 0) {
                         console.warn("allImages is empty, skipping shuffle");
                         return;
                    }
                    const shuffledImages = shuffleArray(images);
                    const shuffled = shuffledImages.slice(0, MAX_GALLERY_IMAGES).map((src, index) => ({
                         id: index + 1,
                         src,
                         aspect: aspectRatios[index % aspectRatios.length],
                    }));
                    setGalleryImages(shuffled);
               } catch (error) {
                    console.error("Error shuffling gallery images:", error);
                    // Keep default images on error
               }
          };

          // Use requestIdleCallback if available, otherwise setTimeout
          // Wrap in try-catch for better mobile compatibility
          try {
               if (typeof window !== 'undefined' && 'requestIdleCallback' in window && typeof window.requestIdleCallback === 'function') {
                    requestIdleCallback(shuffleAndSetImages, { timeout: 1000 });
               } else {
                    setTimeout(shuffleAndSetImages, 100);
               }
          } catch (error) {
               // Fallback to setTimeout if requestIdleCallback fails
               console.warn("requestIdleCallback failed, using setTimeout:", error);
               setTimeout(shuffleAndSetImages, 100);
          }
     }, []);

     // Resolution options - API only supports 480p, 720p, 1080p (no aspect ratio selection)
     const allResolutionOptions = [
          { label: "480p", value: "480p" },
          { label: "720p", value: "720p" },
          { label: "1080p", value: "1080p" },
     ];

     // Duration options (Wan 2.5 Image To Video supports 3-10 seconds)
     const durationOptions = [3, 4, 5, 6, 7, 8, 9, 10];

     // Get available resolutions for selected model
     const getAvailableResolutions = () => {
          if (!selectedModel) return allResolutionOptions;
          return allResolutionOptions.filter(opt => 
               selectedModel.supported_resolutions.includes(opt.value)
          );
     };

     // Get available durations for selected model
     const getAvailableDurations = () => {
          if (!selectedModel) return [3, 4, 5, 6, 7, 8, 9, 10];
          return selectedModel.supported_durations;
     };

     // Mobile detection for model dropdown positioning
     useEffect(() => {
          const checkMobile = () => {
               setIsMobile(window.innerWidth < 1024);
          };
          checkMobile();
          window.addEventListener('resize', checkMobile);
          return () => window.removeEventListener('resize', checkMobile);
     }, []);

     // Load available models on mount
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
               // Update to model's default aspect ratio if model uses aspect ratio
               if (selectedModel.uses_aspect_ratio) {
                    setAspectRatio(selectedModel.default_aspect_ratio || "16:9");
               }
          }
     }, [selectedModel]);

     // Pre-fetch credit costs for all available resolutions when model or duration changes
     useEffect(() => {
          if (selectedModel && duration) {
               const modelId = selectedModel.id;
               const availableResolutions = getAvailableResolutions();
               const availableDurations = getAvailableDurations();
               
               // Pre-fetch credits for all available resolutions and durations
               availableResolutions.forEach(opt => {
                    availableDurations.forEach((dur: number) => {
                         const resolution = convertSizeToResolution(opt.value);
                         const cacheKey = `${modelId}-${resolution}-${dur}`;
                         
                         // Only fetch if not already cached
                         if (!creditCache.has(cacheKey)) {
                              getRequiredCredits(opt.value, dur).catch(() => {
                                   // Silently handle errors - function returns 0 as fallback
                              });
                         }
                    });
               });
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [selectedModel, duration]);

     // Cleanup blob URLs on component unmount to prevent memory leaks
     useEffect(() => {
          return () => {
               // Revoke image preview blob URL
               if (imagePreview && imagePreview.startsWith('blob:')) {
                    try {
                         URL.revokeObjectURL(imagePreview);
                         console.log("🧹 Cleaned up image preview blob URL on unmount");
                    } catch (e) {
                         console.warn("Failed to revoke image blob URL on unmount:", e);
                    }
               }
               // Revoke audio preview blob URL
               if (audioPreview && audioPreview.startsWith('blob:')) {
                    try {
                         URL.revokeObjectURL(audioPreview);
                         console.log("🧹 Cleaned up audio preview blob URL on unmount");
                    } catch (e) {
                         console.warn("Failed to revoke audio blob URL on unmount:", e);
                    }
               }
          };
     }, [imagePreview, audioPreview]);

     const loadModels = async () => {
          try {
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/image-to-video/models`);
               const data = await response.json();
               
               if (response.ok && data.models) {
                    setModels(data.models);
                    if (data.models.length > 0) {
                         setSelectedModel(data.models[0]);
                         setSize(data.models[0].default_resolution);
                         setDuration(data.models[0].default_duration);
                    }
               }
          } catch (err) {
               console.error("Error loading models:", err);
          } finally {
               setLoadingModels(false);
          }
     };

     // Convert size format (1280*720) to resolution format (720p)
     // No conversion needed - API uses resolution format directly
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

     const convertSizeToResolution = (sizeValue: string): string => {
          // If already in resolution format (480p, 720p, 1080p), return as is
          if (sizeValue === "480p" || sizeValue === "720p" || sizeValue === "1080p") {
               return sizeValue;
          }
          // Legacy support for width*height format
          const [width, height] = sizeValue.split('*').map(Number);
          if (width <= 832 || height <= 832) {
               return "480p";
          } else if (width <= 1280 || height <= 1280) {
               return "720p";
          } else {
               return "1080p";
          }
     };

     // Fetch required credits from backend
     const getRequiredCredits = async (sizeValue: string, durationValue: number): Promise<number> => {
          if (!selectedModel) {
               return 0;
          }
          
          const resolution = convertSizeToResolution(sizeValue);
          const modelId = selectedModel.id;
          const cacheKey = `${modelId}-${resolution}-${durationValue}`;
          
          // Check cache first
          if (creditCache.has(cacheKey)) {
               return creditCache.get(cacheKey)!;
          }
          
          try {
               const apiUrl = process.env.NEXT_PUBLIC_API_V1_URL;
               if (!apiUrl) {
                    console.warn("NEXT_PUBLIC_API_V1_URL is not defined");
                    return 0;
               }
               
               const response = await fetch(
                    `${apiUrl}/image-to-video/calculate-credits?model_id=${encodeURIComponent(modelId)}&resolution=${encodeURIComponent(resolution)}&duration=${durationValue}`
               );
               
               if (response.ok) {
                    const data = await response.json();
                    const credits = data.credits || 0;
                    // Cache the result
                    setCreditCache(prev => new Map(prev).set(cacheKey, credits));
                    return credits;
               } else {
                    console.warn("Failed to calculate credits:", response.statusText);
               }
          } catch (error: any) {
               // Silently handle network errors - don't spam console
               // The function will return 0 as fallback, which is acceptable
               if (error?.message && !error.message.includes("Failed to fetch")) {
                    console.warn("Error fetching credit cost:", error);
               }
          }
          
          return 0;
     };
     
     // Synchronous version for immediate display (uses cached value or model config from backend)
     const getRequiredCreditsSync = (sizeValue: string, durationValue: number): number => {
          if (!selectedModel) {
               return 0;
          }
          
          const resolution = convertSizeToResolution(sizeValue);
          const modelId = selectedModel.id;
          const cacheKey = `${modelId}-${resolution}-${durationValue}`;
          
          // Check cache first (from API call)
          const cached = creditCache.get(cacheKey);
          if (cached !== undefined && cached > 0) {
               return cached;
          }
          
          // Use model's credit_by_duration from backend config (fetched from /models endpoint)
          if (selectedModel.credit_by_duration) {
               const creditByDuration = selectedModel.credit_by_duration;
               if (typeof creditByDuration === 'object' && creditByDuration[durationValue] !== undefined) {
                    return creditByDuration[durationValue];
               }
          }
          
          // Fallback to credit_cost if available
          if (selectedModel.credit_cost !== undefined) {
               return selectedModel.credit_cost;
          }
          
          return 0;
     };
     // Get button text and action
     const getButtonConfig = () => {
          if (isGenerating) return { text: "Generating...", action: () => {} }; // Prevent action when generating
          if (imageUploading || audioUploading) return { text: "Uploading...", action: () => {} }; // Prevent action when uploading
          
          if (!user) return { text: "Generate", action: () => router.push("/signup") };
          
          const hasSubscription = !!user.plan_name;
          const requiredCredits = getRequiredCreditsSync(size, duration);
          const hasEnoughCredits = (user.credit_balance || 0) >= requiredCredits;
          
          if (!hasSubscription) {
               // Redirect to /upgrade page where user can see all available plans
               return { text: "Get More Credits", action: () => router.push("/upgrade") };
          }
          
          if (!hasEnoughCredits) {
               return { text: "Get More Credits", action: () => router.push("/upgrade") };
          }
          
          return { 
               text: `Generate (${requiredCredits})`, 
               action: handleGenerate 
          };
     };

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
               // Formula: progress = 100 * (1 - e^(-elapsed/estimated_time))
               // This creates a realistic curve that slows down near 100%
               
               const estimatedTime = 120; // 2 minutes average
               const rawProgress = 100 * (1 - Math.exp(-elapsed / estimatedTime));
               
               // Cap at 95% until actually completed (so it doesn't reach 100% before completion)
               const cappedProgress = Math.min(rawProgress, 95);
               
               setProgress(Math.round(cappedProgress));
          };

          // Update immediately
          updateProgress();
          
          // Update every second
          const interval = setInterval(updateProgress, 1000);
          
          return () => clearInterval(interval);
     }, [isGenerating, jobStartTime, outputUrl]);

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
                    // Update both states together to prevent flash
                    setPreviousJobs(data.jobs);
                    setLoadingJobs(false);
                    setHasLoadedOnce(true);
                    
                    // Check for any pending/running jobs and automatically show overlay
                    const runningJob = data.jobs.find((job: any) => 
                         (job.status === "pending" || job.status === "running" || job.status === "processing" || (job.status === "completed" && !job.output_url)) && !job.output_url
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
                         
                         // Restore image preview if available in job settings
                         if (runningJob.settings?.image_url && !imagePreview) {
                              setImagePreview(runningJob.settings.image_url);
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
                              
                              if ((currentJob.status === "pending" || currentJob.status === "running" || currentJob.status === "processing" || (currentJob.status === "completed" && !currentJob.output_url)) && !currentJob.output_url) {
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
                                   cleanupPolling(); // Clean up any existing intervals
                                   // Clean up localStorage
                                   safeLocalStorage.removeItem(`job_start_${jobId}`);
                              } else if (currentJob.status === "failed") {
                                   // Job failed
                                   setError(currentJob.error || "Video generation failed");
                                   setIsGenerating(false);
                                   setIsPolling(false);
                                   cleanupPolling(); // Clean up any existing intervals
                                   // Clean up localStorage
                                   safeLocalStorage.removeItem(`job_start_${jobId}`);
                              }
                         }
                    }
                    
                    if (selectedJob) {
                         const updatedSelectedJob = data.jobs.find((job: any) => job.job_id === selectedJob.job_id);
                         if (updatedSelectedJob) {
                              setSelectedJob(updatedSelectedJob);
                              if (updatedSelectedJob.status === "completed" && updatedSelectedJob.output_url) {
                                   setOutputUrl(updatedSelectedJob.output_url);
                                   setJobStatus("completed");
                              }
                         }
                    }
               } else {
                    // If response is not ok or no jobs, set empty array and stop loading
                    setPreviousJobs([]);
                    setLoadingJobs(false);
                    setHasLoadedOnce(true);
               }
          } catch (err) {
               console.error("Error loading previous jobs:", err);
               setPreviousJobs([]);
               setLoadingJobs(false);
               setHasLoadedOnce(true);
          }
     };

     const uploadFileToBackblaze = async (file: File, isAudio: boolean = false) => {
          const token = getToken();
          if (!token) {
               router.push("/login");
               return null;
          }

          const formData = new FormData();
          formData.append("file", file);

          try {
               // Use text-to-video endpoint for audio (same storage bucket)
               const endpoint = isAudio 
                    ? `${process.env.NEXT_PUBLIC_API_V1_URL}/storage/upload/text-to-video`
                    : `${process.env.NEXT_PUBLIC_API_V1_URL}/storage/upload/image-to-video`;
               
               const response = await fetch(endpoint, {
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
               console.error(`Error uploading ${isAudio ? 'audio' : 'image'}:`, err);
               setError(`Failed to upload ${isAudio ? 'audio' : 'image'}: ${err.message}`);
               return null;
          }
     };

     const handleImageSelect = async (file: File) => {
          if (!file.type.startsWith("image/")) {
               setError("Please select an image file (JPG, PNG, etc.)");
               // Reset input to allow reselection
               if (imageInputRef.current) {
                    imageInputRef.current.value = '';
               }
               return;
          }

          // Check file size (10 MB limit)
          if (file.size > 10 * 1024 * 1024) {
               setError("Image file must be 10 MB or less");
               // Reset input to allow reselection
               if (imageInputRef.current) {
                    imageInputRef.current.value = '';
               }
               return;
          }

          // Clear old image data IMMEDIATELY before setting new one
          // This ensures the old Backblaze URL is not used
          const oldUrl = imageUrlRef.current;
          const oldPreview = imagePreview;
          console.log("🗑️ Clearing old image. Previous URL was:", oldUrl);
          
          // Revoke old preview blob URL to prevent memory leaks
          if (oldPreview && oldPreview.startsWith('blob:')) {
               try {
                    URL.revokeObjectURL(oldPreview);
                    console.log("🧹 Revoked old preview blob URL");
               } catch (e) {
                    console.warn("Failed to revoke blob URL:", e);
               }
          }
          
          // Clear ref FIRST (synchronous, immediate) - this prevents any old URL from being used
          imageUrlRef.current = null;
          uploadTimestampRef.current = 0; // Reset timestamp
          
          // Then clear state (triggers useEffect to sync)
          setImageFile(null);
          setImagePreview(null);
          setImageUrl(null);
          setError(null);
          
          console.log("✅ Old image cleared. Ref is now:", imageUrlRef.current);

          // Set new file (but DON'T upload yet - wait for Generate button)
          setImageFile(file);

          // Create preview (same pattern as /image page - simple and works)
          const reader = new FileReader();
          reader.onload = (e) => {
               setImagePreview(e.target?.result as string);
               console.log("✅ Image preview created");
          };
          reader.onerror = (e) => {
               console.error("❌ Failed to create image preview:", e);
               setError("Failed to load image preview");
          };
          reader.readAsDataURL(file);
          
          // Reset the file input immediately after reading the file
          // This allows the user to select the same file again if needed
          if (imageInputRef.current) {
               imageInputRef.current.value = '';
               console.log("🔄 File input reset to allow reselection");
          }
          
          console.log("✅ Image file selected and preview created. Upload will happen when Generate is clicked.");
     };

     const handleAudioSelect = async (file: File) => {
          if (!file.type.startsWith("audio/")) {
               setError("Please select an audio file (WAV or MP3)");
               // Reset input to allow reselection
               if (audioInputRef.current) {
                    audioInputRef.current.value = '';
               }
               return;
          }

          // Check file size (15 MB limit)
          if (file.size > 15 * 1024 * 1024) {
               setError("Audio file must be 15 MB or less");
               // Reset input to allow reselection
               if (audioInputRef.current) {
                    audioInputRef.current.value = '';
               }
               return;
          }

          // Clear old audio data before setting new one
          // This ensures the old Backblaze URL is not used if upload is cancelled
          const oldPreview = audioPreview;
          
          // Revoke old preview blob URL to prevent memory leaks
          if (oldPreview && oldPreview.startsWith('blob:')) {
               try {
                    URL.revokeObjectURL(oldPreview);
                    console.log("🧹 Revoked old audio preview blob URL");
               } catch (e) {
                    console.warn("Failed to revoke audio blob URL:", e);
               }
          }
          
          setAudioFile(null);
          setAudioPreview(null);
          setAudioUrl(null);
          setError(null);

          // Set new file and start upload
          setAudioFile(file);
          setAudioUploading(true);

          // Create preview
          const reader = new FileReader();
          reader.onload = (e) => {
               setAudioPreview(e.target?.result as string);
               console.log("✅ Audio preview created");
          };
          reader.onerror = (e) => {
               console.error("❌ Failed to create audio preview:", e);
               setError("Failed to load audio preview");
          };
          reader.readAsDataURL(file);

          // Reset the file input immediately after reading the file
          // This allows the user to select the same file again if needed
          if (audioInputRef.current) {
               audioInputRef.current.value = '';
               console.log("🔄 Audio file input reset to allow reselection");
          }

          // Upload to Backblaze immediately
          const url = await uploadFileToBackblaze(file, true);
          if (url) {
               setAudioUrl(url);
               console.log("✅ Audio uploaded to Backblaze:", url);
               // Old URL is already cleared above, so new URL will be used
          } else {
               // If upload failed, restore previous state or clear everything
               setAudioFile(null);
               setAudioPreview(null);
               setAudioUrl(null);
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

          if (!imageFile && !imageUrl) {
               setError("Please select an image first");
               return;
          }

          if (!prompt.trim()) {
               setError("Please enter a prompt");
               return;
          }

          if (!selectedModel) {
               setError("Please select a model");
               return;
          }

          const token = getToken();
          if (!token) {
               router.push("/login");
               return;
          }

          // CRITICAL: Clean up any existing polling intervals before starting new generation
          console.log("🔄 Starting new generation - cleaning up old polling intervals");
          cleanupPolling();
          setIsPolling(false);

          // Set ref immediately to prevent double submission
          isSubmittingRef.current = true;
          setError(null);
          setOutputUrl(null);
          setJobStatus(null);
          
          // Save current image data for upload, but keep preview visible
          const currentImageFile = imageFile;
          const currentImageUrl = imageUrlRef.current || imageUrl;
          
          // Clear only the file object to allow new uploads, but keep preview and URL visible
          setImageFile(null);
          // Reset the file input to allow reselecting the same file
          if (imageInputRef.current) {
               imageInputRef.current.value = '';
          }

          try {
               // Upload image to Backblaze if we have a file but no URL yet
               let finalImageUrl = currentImageUrl;
               
               if (currentImageFile && !finalImageUrl) {
                    console.log("📤 Uploading image to Backblaze before generation...");
                    setImageUploading(true);
                    
                    try {
                         const uploadStartTime = Date.now();
                         const url = await uploadFileToBackblaze(currentImageFile, false);
                         
                         if (url) {
                              // Set ref FIRST (synchronous, immediate) - this is the source of truth
                              imageUrlRef.current = url;
                              uploadTimestampRef.current = uploadStartTime; // Mark when this upload happened
                              
                              // Then set state (triggers useEffect to sync, but ref is already set)
                              setImageUrl(url);
                              
                              finalImageUrl = url;
                              console.log("✅ Image uploaded to Backblaze:", url);
                              console.log("✅ Upload timestamp:", uploadTimestampRef.current);
                         } else {
                              throw new Error("Failed to upload image to Backblaze");
                         }
                    } catch (uploadError: any) {
                         console.error("❌ Image upload failed:", uploadError);
                         throw new Error(`Failed to upload image: ${uploadError.message || "Unknown error"}`);
                    } finally {
                         setImageUploading(false);
                    }
               }
               
               // Now set generating state after upload is complete
               setIsGenerating(true);
               
               if (!finalImageUrl) {
                    throw new Error("No image URL available. Please select an image first.");
               }
               
               // Convert size format to resolution format for API
               const resolution = convertSizeToResolution(size);
               
               console.log("🚀 Generating video...");
               console.log("🚀 Using image URL:", finalImageUrl);
               console.log("🚀 Upload timestamp:", uploadTimestampRef.current);
               
               const requestBody: any = {
                    prompt: prompt,
                    model: selectedModel.id,
                    image_url: finalImageUrl, // Always use ref (most up-to-date, synchronous)
                    resolution: resolution, // API expects "480p", "720p", or "1080p"
                    duration: duration,
                    seed: -1,
                    enable_prompt_expansion: enablePromptExpansion,
               };

               // Add optional parameters
               if (negativePrompt.trim()) {
                    requestBody.negative_prompt = negativePrompt;
               }
               if (audioUrl) {
                    requestBody.audio_url = audioUrl;
               }
               // Add aspect_ratio for models that use it (e.g., Google Veo)
               if (selectedModel?.uses_aspect_ratio && aspectRatio) {
                    requestBody.aspect_ratio = aspectRatio;
               }

               // Add timeout to submit request (30 seconds)
               const abortController = new AbortController();
               const submitTimeout = setTimeout(() => abortController.abort(), 30000);

               let response;
               try {
                    response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/image-to-video/submit`, {
                         method: "POST",
                         headers: {
                              "Content-Type": "application/json",
                              "Authorization": `Bearer ${token}`
                         },
                         body: JSON.stringify(requestBody),
                         signal: abortController.signal
                    });
                    clearTimeout(submitTimeout);
               } catch (fetchError: any) {
                    clearTimeout(submitTimeout);
                    if (fetchError.name === 'AbortError') {
                         throw new Error("Request timed out. Please try again.");
                    }
                    throw fetchError;
               }

               const data = await response.json();

               if (!response.ok) {
                    throw new Error(data.detail || "Failed to submit job");
               }

               setJobId(data.job_id);
               setJobStatus(data.status);
               setSelectedJob(data);
               
               // Image already cleared at start of handleGenerate, no need to clear again
               
               // Store job start time for progress calculation (persists across refreshes)
               const startTime = Date.now();
               setJobStartTime(startTime);
               // Store in localStorage for persistence across refreshes
               if (data.job_id) {
                    safeLocalStorage.setItem(`job_start_${data.job_id}`, startTime.toString());
               }

               // Start polling for status
               setIsPolling(true);
               pollJobStatus(data.job_id);

               // Reload jobs list after a short delay to avoid race conditions
               setTimeout(() => {
                    loadPreviousJobs();
               }, 1000);
          } catch (err: any) {
               console.error("Error generating video:", err);
               setError(err.message || "Failed to generate video");
               setIsGenerating(false);
               setImageUploading(false);
               isSubmittingRef.current = false; // Reset ref on error
          }
     };

     const pollJobStatus = async (jobIdToPoll: string) => {
          const token = getToken();
          if (!token) return;

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
                    const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/image-to-video/jobs/${jobIdToPoll}`, {
                         headers: {
                              "Authorization": `Bearer ${token}`
                         },
                         signal: abortController.signal
                    });

                    clearTimeout(requestTimeout);
                    const data = await response.json();

                    if (response.ok && data) {
                         setJobStatus(data.status);
                         setSelectedJob(data);

                         if (data.status === "completed" && data.output_url) {
                              setOutputUrl(data.output_url);
                              setProgress(100);
                              setIsGenerating(false);
                              setIsPolling(false);
                              isSubmittingRef.current = false; // Reset ref when completed
                              cleanupPolling(); // Use cleanup function
                              // Clean up localStorage
                              if (jobIdToPoll) {
                                   safeLocalStorage.removeItem(`job_start_${jobIdToPoll}`);
                              }
                              loadPreviousJobs();
                         } else if (data.status === "failed") {
                              setError(data.error || "Video generation failed");
                              setIsGenerating(false);
                              setIsPolling(false);
                              isSubmittingRef.current = false; // Reset ref on failure
                              cleanupPolling(); // Use cleanup function
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
                    // Handle timeout specifically
                    if (err.name === 'AbortError') {
                         console.warn("Request timeout during polling, will retry on next poll");
                         // Don't stop polling - continue trying
                    } else {
                         console.error("Error polling job status:", err);
                         // Don't stop polling on error - continue trying
                    }
               }
          };

          // Poll immediately, then every 3 seconds
          poll();
          pollIntervalRef.current = setInterval(poll, POLL_INTERVAL);
          console.log("✅ Started polling interval:", pollIntervalRef.current);

          // Overall timeout after 10 minutes
          pollTimeoutRef.current = setTimeout(() => {
               cleanupPolling(); // Use cleanup function
               const currentStatus = jobStatus;
               if (currentStatus !== "completed" && currentStatus !== "failed") {
                    setError("Job is taking longer than expected. You can check back later or refresh the page to see the status.");
                    setIsGenerating(false);
                    setIsPolling(false);
                    isSubmittingRef.current = false;
                    // Don't remove job from localStorage - user can check back later
                    console.log("Polling timeout reached, but job may still be processing on the server");
               }
          }, MAX_POLL_TIME);
          console.log("✅ Started polling timeout:", pollTimeoutRef.current);
     };

     // Handle drag and drop for images
     useEffect(() => {
          const dropZone = imageDropRef.current;
          if (!dropZone) return;

          const handleDragOver = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.add("border-blue-1100");
          };

          const handleDragLeave = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.remove("border-blue-1100");
          };

          const handleDrop = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.remove("border-blue-1100");

               const files = e.dataTransfer?.files;
               if (files && files.length > 0) {
                    handleImageSelect(files[0]);
               }
          };

          dropZone.addEventListener("dragover", handleDragOver);
          dropZone.addEventListener("dragleave", handleDragLeave);
          dropZone.addEventListener("drop", handleDrop);

          return () => {
               dropZone.removeEventListener("dragover", handleDragOver);
               dropZone.removeEventListener("dragleave", handleDragLeave);
               dropZone.removeEventListener("drop", handleDrop);
          };
     }, []);

     // Handle drag and drop for audio
     useEffect(() => {
          const dropZone = audioDropRef.current;
          if (!dropZone) return;

          const handleDragOver = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.add("border-blue-1100", "bg-blue-1100/10");
          };

          const handleDragLeave = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.remove("border-blue-1100", "bg-blue-1100/10");
          };

          const handleDrop = (e: DragEvent) => {
               e.preventDefault();
               e.stopPropagation();
               dropZone.classList.remove("border-blue-1100", "bg-blue-1100/10");

               const files = e.dataTransfer?.files;
               if (files && files.length > 0) {
                    const file = files[0];
                    if (file.type.startsWith("audio/")) {
                         handleAudioSelect(file);
                    } else {
                         setError("Please drop an audio file");
                    }
               }
          };

          dropZone.addEventListener("dragover", handleDragOver);
          dropZone.addEventListener("dragleave", handleDragLeave);
          dropZone.addEventListener("drop", handleDrop);

          return () => {
               dropZone.removeEventListener("dragover", handleDragOver);
               dropZone.removeEventListener("dragleave", handleDragLeave);
               dropZone.removeEventListener("drop", handleDrop);
          };
     }, []);

     const buttonConfig = getButtonConfig();

     return (
          <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
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
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Input Image</h3>
                                   <div 
                                        ref={imageDropRef}
                                        onClick={() => imageInputRef.current?.click()}
                                        className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-6 text-center cursor-pointer hover:border-blue-1100 transition-colors"
                                   >
                                        <input
                                             ref={imageInputRef}
                                             type="file"
                                             accept="image/*"
                                             className="hidden"
                                             onChange={(e) => {
                                                  const file = e.target.files?.[0];
                                                  if (file) handleImageSelect(file);
                                             }}
                                        />
                                        {imagePreview ? (
                                             <div className="relative">
                                                  <img src={imagePreview} alt="Preview" className="w-full h-32 object-cover rounded-lg mb-2" />
                                                  <button
                                                       onClick={(e) => {
                                                            e.stopPropagation();
                                                            setImageFile(null);
                                                            setImagePreview(null);
                                                            setImageUrl(null);
                                                            imageUrlRef.current = null; // Clear ref when removing image
                                                       }}
                                                       className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white p-1 rounded"
                                                  >
                                                       ×
                                                  </button>
                                             </div>
                                        ) : (
                                             <>
                                        <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400">
                                             <img src="/images/image-icon.svg" alt="" />
                                             <div className="bg-gray-1500/[30%] flex items-center backdrop-blur-[8px] justify-center w-4 h-4 rounded-full absolute -top-2 -right-2">
                                                  <img src="/images/Plus.svg" alt="" />
                                             </div>
                                        </div>
                                        <h6 className="text-xs font-medium leading-[120%] text-white mt-2.5 mb-1">Upload Reference Image</h6>
                                        <p className="text-xs max-w-[177px] mx-auto font-normal leading-[120%] text-white/60">Add a photo of yourself or any image you want to animate.</p>
                                             </>
                                        )}
                                   </div>
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
                                                       <span className="block truncate text-sm font-medium">{selectedModel.display_name}</span>
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
                                                                      <span className="text-sm font-medium text-white">{model.display_name}</span>
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
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Prompt</h3>
                                   <textarea
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        className="w-full h-32 rounded-lg border border-gray-1100 bg-black-1000 p-3 text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                        placeholder="Describe the video you want to generate..."
                                   />
                              </div>
                              {selectedModel?.supports_negative_prompt && (
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Negative Prompt (Optional)</h3>
                                   <textarea
                                        value={negativePrompt}
                                        onChange={(e) => setNegativePrompt(e.target.value)}
                                        className="w-full h-24 rounded-lg border border-gray-1100 bg-black-1000 p-3 text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                        placeholder="What you don't want in the video..."
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
                                             const files = e.dataTransfer?.files;
                                             if (files && files.length > 0) {
                                                  handleAudioSelect(files[0]);
                                             }
                                        }}
                                        className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-4 text-center cursor-pointer hover:border-blue-1100 transition-colors"
                                   >
                                        {audioPreview ? (
                                             <div className="relative">
                                                  <div className="flex items-center gap-2 text-white text-xs">
                                                       <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                            <path d="M9 18V5l12-2v13"></path>
                                                            <circle cx="6" cy="18" r="3"></circle>
                                                            <circle cx="18" cy="16" r="3"></circle>
                                                       </svg>
                                                       <span>Audio file selected</span>
                                                  </div>
                                                  <button
                                                       onClick={(e) => {
                                                            e.stopPropagation();
                                                            setAudioFile(null);
                                                            setAudioPreview(null);
                                                            setAudioUrl(null);
                                                       }}
                                                       className="absolute top-0 right-0 bg-black/60 hover:bg-black/80 text-white p-1 rounded"
                                                  >
                                                       ×
                                                  </button>
                                             </div>
                                        ) : (
                                             <>
                                                  <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400">
                                                       <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                            <path d="M9 18V5l12-2v13"></path>
                                                            <circle cx="6" cy="18" r="3"></circle>
                                                            <circle cx="18" cy="16" r="3"></circle>
                                                       </svg>
                                                       <div className="bg-gray-1500/[30%] flex items-center backdrop-blur-[8px] justify-center w-4 h-4 rounded-full absolute -top-2 -right-2">
                                                            <img src="/images/Plus.svg" alt="" />
                                                       </div>
                                                  </div>
                                                  <h6 className="text-xs font-medium leading-[120%] text-white mt-2.5 mb-1">Upload Audio File</h6>
                                                  <p className="text-xs max-w-[177px] mx-auto font-normal leading-[120%] text-white/60">WAV or MP3, 3-30 seconds, ≤15 MB</p>
                                             </>
                                        )}
                                   </div>
                              </div>
                              )}
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Resolution</h3>
                                   <div className="grid grid-cols-3 gap-1">
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
                                                       <span className="text-white/60">({credits})</span>
                                             </button>
                                             );
                                        })}
                                   </div>
                              </div>
                              <div className="mb-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Duration</h3>
                                        <div className="grid grid-cols-4 gap-1">
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
                              {selectedModel?.uses_aspect_ratio && (
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Aspect Ratio</h3>
                                   <div className="grid grid-cols-2 gap-1">
                                        {(selectedModel.supported_aspect_ratios || ["16:9", "9:16"]).map((ratio: string) => (
                                             <button
                                                  key={ratio}
                                                  type="button"
                                                  onClick={() => setAspectRatio(ratio)}
                                                  className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
                                                       ${aspectRatio === ratio ? "bg-gray-1100/30! border-blue-1100!" : ""} 
                                                  `}
                                             >
                                                  {ratio}
                                             </button>
                                        ))}
                                   </div>
                              </div>
                              )}
                              {selectedModel?.supports_prompt_expansion && (
                              <div className="mb-6">
                                   <div className="flex items-center gap-2 mb-2">
                                        <input
                                             type="checkbox"
                                             id="enablePromptExpansion"
                                             checked={enablePromptExpansion}
                                             onChange={(e) => setEnablePromptExpansion(e.target.checked)}
                                             className="w-4 h-4 rounded border-gray-1100 bg-black-1000 text-blue-1100 focus:ring-blue-1100 focus:ring-offset-0"
                                        />
                                        <label htmlFor="enablePromptExpansion" className="text-xs font-normal leading-[120%] text-white/60 cursor-pointer">
                                             Enable Prompt Expansion
                                        </label>
                                   </div>
                                   <p className="text-[10px] text-white/40 ml-6">Optimize your prompt automatically for better results</p>
                              </div>
                              )}
                              {error && (
                                   <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                                        {error}
                                   </div>
                              )}
                         </div>
                         <div className="text-center lg:pb-0" style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom, 0px))' }}>
                              <button 
                                   onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        if (!isGenerating && !imageUploading && !audioUploading && !isSubmittingRef.current) {
                                             buttonConfig.action();
                                        }
                                   }}
                                   disabled={isGenerating || imageUploading || audioUploading || isSubmittingRef.current}
                                   className={clsx(
                                        "relative md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl transition-all duration-300 overflow-hidden",
                                        (isGenerating || imageUploading || audioUploading || isSubmittingRef.current) 
                                             ? "cursor-not-allowed" 
                                             : "hover:shadow-7xl"
                                   )}
                              >
                                   {isGenerating || imageUploading || audioUploading ? (
                                        <>
                                             <span className="relative z-10">{buttonConfig.text}</span>
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                                        </>
                                   ) : (
                                        buttonConfig.text
                                   )}
                              </button>
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
                                        onSelectJob={(job) => {
                                             setSelectedJob(job);
                                             // Restore settings if retrying a failed job
                                             if (job && (job.status === 'failed' || job.status === 'completed')) {
                                                  // Restore prompt
                                                  if (job.input_prompt || job.prompt) {
                                                       setPrompt(job.input_prompt || job.prompt);
                                                  }
                                                  
                                                  // Restore settings from job object or settings dict
                                                  const settings = job.settings || job;
                                                  if (settings) {
                                                       if (settings.size) setSize(settings.size);
                                                       if (settings.duration) setDuration(settings.duration);
                                                       if (settings.negative_prompt) setNegativePrompt(settings.negative_prompt);
                                                       if (settings.enable_prompt_expansion !== undefined) {
                                                            setEnablePromptExpansion(settings.enable_prompt_expansion);
                                                       }
                                                       if (settings.aspect_ratio) setAspectRatio(settings.aspect_ratio);
                                                       
                                                       // Restore model if available
                                                       if ((settings.model || settings.model_id) && models.length > 0) {
                                                            const modelId = settings.model || settings.model_id;
                                                            const model = models.find(m => m.id === modelId);
                                                            if (model) setSelectedModel(model);
                                                       }
                                                       
                                                       // Restore image preview if available
                                                       if (settings.image_url && !imagePreview) {
                                                            setImagePreview(settings.image_url);
                                                            setImageUrl(settings.image_url);
                                                            imageUrlRef.current = settings.image_url;
                                                       }
                                                  }
                                                  
                                                  // Open sidebar on mobile
                                                  if (window.innerWidth < 1024) {
                                                       setSidebarOpen(true);
                                                  }
                                             }
                                        }}
                                   />
                              </div>
                         ) : previousJobs.length > 0 || outputUrl || (isGenerating && imagePreview) ? (
                              <div className="w-full max-w-[1320px] mx-auto">
                                   <div className="md:hidden block mb-6 px-5" style={{ paddingBottom: 'max(1.5rem, calc(1.5rem + env(safe-area-inset-bottom, 0px)))' }}>
                         <div className="text-center mb-6">
                                             <div className="flex gap-2 items-center justify-center mb-2">
                                   <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">NEW</span>
                                                  <h6 className="text-sm font-normal leading-[120%] text-gradient">Image to Video</h6>
                                             </div>
                                             <h2 className="text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Turn Any Image Into Motion</h2>
                                             <p className="text-sm font-medium leading-[120%] text-white/60 mb-6">Turn images into high-impact creative videos powered by the latest AI models.</p>
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
                                        onSelectJob={(job) => {
                                             setSelectedJob(job);
                                             // Restore settings if retrying a failed job
                                             if (job && (job.status === 'failed' || job.status === 'completed')) {
                                                  // Restore prompt
                                                  if (job.input_prompt || job.prompt) {
                                                       setPrompt(job.input_prompt || job.prompt);
                                                  }
                                                  
                                                  // Restore settings from job object or settings dict
                                                  const settings = job.settings || job;
                                                  if (settings) {
                                                       if (settings.size) setSize(settings.size);
                                                       if (settings.duration) setDuration(settings.duration);
                                                       if (settings.negative_prompt) setNegativePrompt(settings.negative_prompt);
                                                       if (settings.enable_prompt_expansion !== undefined) {
                                                            setEnablePromptExpansion(settings.enable_prompt_expansion);
                                                       }
                                                       if (settings.aspect_ratio) setAspectRatio(settings.aspect_ratio);
                                                       
                                                       // Restore model if available
                                                       if ((settings.model || settings.model_id) && models.length > 0) {
                                                            const modelId = settings.model || settings.model_id;
                                                            const model = models.find(m => m.id === modelId);
                                                            if (model) setSelectedModel(model);
                                                       }
                                                       
                                                       // Restore image preview if available
                                                       if (settings.image_url && !imagePreview) {
                                                            setImagePreview(settings.image_url);
                                                            setImageUrl(settings.image_url);
                                                            imageUrlRef.current = settings.image_url;
                                                       }
                                                  }
                                                  
                                                  // Open sidebar on mobile
                                                  if (window.innerWidth < 1024) {
                                                       setSidebarOpen(true);
                                                  }
                                             }
                                        }}
                                   />
                              </div>
                         ) : (
                              <>
                                   <div className="text-center mb-6 pt-4 md:pt-0">
                                        <div className="flex gap-2 items-center justify-center">
                                             <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">NEW</span>
                                             <h6 className="text-sm font-normal leading-[120%] text-gradient">Image to Video</h6>
                              </div>
                              <h2 className="md:text-5xl text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Turn Any Image Into Motion</h2>
                                        <p className="md:text-base text-sm font-medium leading-[120%] text-white/60">Turn images into high-impact creative videos powered by the latest AI models.</p>
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
                         
                         {/* Generating indicator - shows on both pages - always visible when generating */}
                         {isGenerating && !outputUrl && jobId && (
                              <div className="fixed bottom-8 right-8 z-50 bg-black-1000 border border-gray-1100 p-4 rounded-xl shadow-2xl w-[320px] animate-in slide-in-from-bottom-4">
                                   <div className="flex items-center gap-4 mb-3">
                                        <div className="w-12 h-12 rounded-lg overflow-hidden relative flex-shrink-0">
                                             {imagePreview ? (
                                                  <>
                                                       <img src={imagePreview} className="w-full h-full object-cover opacity-50" alt="" />
                                                       <div className="absolute inset-0 flex items-center justify-center">
                                                            <div className="w-6 h-6 border-2 border-blue-1100 border-t-transparent rounded-full animate-spin"></div>
                                                       </div>
                                                  </>
                                             ) : (
                                                  <div className="w-full h-full bg-gray-1100 flex items-center justify-center">
                                                       <div className="w-6 h-6 border-2 border-blue-1100 border-t-transparent rounded-full animate-spin"></div>
                                                  </div>
                                             )}
                                   </div>
                                        <div className="flex-1 min-w-0">
                                             <h4 className="text-sm font-medium text-white">Generating Video...</h4>
                                             <p className="text-xs text-white/60">{progress}% complete</p>
                              </div>
                                   </div>
                                   {/* Progress bar */}
                                   <div className="w-full h-1.5 bg-gray-1200/30 rounded-full overflow-hidden">
                                        <div 
                                             className="h-full bg-gradient-to-r from-blue-1100 to-blue-1000 rounded-full transition-all duration-1000 ease-out"
                                             style={{ width: `${progress}%` }}
                                        />
                                   </div>
                              </div>
                         )}
                    </div>
               </section>
          </div>
     )
}

export default Page
