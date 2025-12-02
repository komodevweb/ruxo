"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import clsx from 'clsx';
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import VideoGallery from "@/app/components/VideoGallery";

function page() {
     const { user, loading: authLoading } = useAuth();
     const router = useRouter();
     const [active, setActive] = useState("720p");
     const [mode, setMode] = useState("animate");
     const [prompt, setPrompt] = useState("");
     const [imageFile, setImageFile] = useState<File | null>(null);
     const [videoFile, setVideoFile] = useState<File | null>(null);
     const [imagePreview, setImagePreview] = useState<string | null>(null);
     const [videoPreview, setVideoPreview] = useState<string | null>(null);
     const [imageUrl, setImageUrl] = useState<string | null>(null);
     const [videoUrl, setVideoUrl] = useState<string | null>(null);
     const imageUrlRef = useRef<string | null>(null); // Ref to track current image URL
     const videoUrlRef = useRef<string | null>(null); // Ref to track current video URL
     const imageUploadTimestampRef = useRef<number>(0); // Track when image was uploaded
     const videoUploadTimestampRef = useRef<number>(0); // Track when video was uploaded
     const isSubmittingRef = useRef<boolean>(false); // Prevent double submission
     
     // Keep refs in sync with state to ensure we always have the latest URLs
     useEffect(() => {
          imageUrlRef.current = imageUrl;
          if (imageUrl) {
               console.log("🔄 Image URL ref synced with state:", imageUrl);
          }
     }, [imageUrl]);
     
     useEffect(() => {
          videoUrlRef.current = videoUrl;
          if (videoUrl) {
               console.log("🔄 Video URL ref synced with state:", videoUrl);
          }
     }, [videoUrl]);
     
     // Ensure template videos play after mount
     useEffect(() => {
          const playVideos = async () => {
               try {
                    if (uploadVideoRef.current) {
                         uploadVideoRef.current.load();
                         await uploadVideoRef.current.play();
                         console.log('Upload video template started playing');
                    }
                    if (bringToLifeVideoRef.current) {
                         bringToLifeVideoRef.current.load();
                         await bringToLifeVideoRef.current.play();
                         console.log('Bring to life video started playing');
                    }
               } catch (err) {
                    console.error('Error playing template videos:', err);
               }
          };
          
          // Delay to ensure DOM is ready
          const timer = setTimeout(playVideos, 500);
          return () => clearTimeout(timer);
     }, []);
     
     const [imageUploading, setImageUploading] = useState(false);
     const [videoUploading, setVideoUploading] = useState(false);
     const [isGenerating, setIsGenerating] = useState(false);
     const [error, setError] = useState<string | null>(null);
     const [jobId, setJobId] = useState<string | null>(null);
     const [outputUrl, setOutputUrl] = useState<string | null>(null);
     const [jobStatus, setJobStatus] = useState<"pending" | "running" | "completed" | "failed" | null>(null);
     const [jobStartTime, setJobStartTime] = useState<number | null>(null);
     const [progress, setProgress] = useState(0);
     const [previousJobs, setPreviousJobs] = useState<any[]>([]);
     const [selectedJob, setSelectedJob] = useState<any | null>(null);
     const [isPolling, setIsPolling] = useState(false);
     const [rateLimited, setRateLimited] = useState(false);
     const [loadingJobs, setLoadingJobs] = useState(true);
     const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
     const imageInputRef = useRef<HTMLInputElement>(null);
     const videoInputRef = useRef<HTMLInputElement>(null);
     const imageDropRef = useRef<HTMLDivElement>(null);
     const videoDropRef = useRef<HTMLDivElement>(null);
     const uploadVideoRef = useRef<HTMLVideoElement>(null);
     const bringToLifeVideoRef = useRef<HTMLVideoElement>(null);
     const uploadVideoPlayCount = useRef(0);
     const bringToLifeVideoPlayCount = useRef(0);
     const options = ["480p", "720p"]; // Only 480p and 720p supported by WaveSpeed
     const [sidebarOpen, setSidebarOpen] = useState(false);

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

     const [creditCache, setCreditCache] = useState<Map<string, number>>(new Map());
     
     // Fetch required credits from backend
     const getRequiredCredits = async (resolution: string): Promise<number> => {
          const cacheKey = `wan-animate-${resolution}`;
          
          // Check cache first
          if (creditCache.has(cacheKey)) {
               return creditCache.get(cacheKey)!;
          }
          
          try {
               const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_V1_URL}/wan-animate/calculate-credits?resolution=${encodeURIComponent(resolution)}`
               );
               
               if (response.ok) {
                    const data = await response.json();
                    const credits = data.credits || 22;
                    // Cache the result
                    setCreditCache(prev => new Map(prev).set(cacheKey, credits));
                    return credits;
               }
          } catch (error) {
               console.error("Error fetching credit cost:", error);
          }
          
          // Fallback based on resolution
          return resolution === "480p" ? 12 : 22;
     };
     
     // Synchronous version for immediate display (uses cached value or returns default)
     const getRequiredCreditsSync = (resolution: string): number => {
          const cacheKey = `wan-animate-${resolution}`;
          const cached = creditCache.get(cacheKey);
          if (cached !== undefined) return cached;
          // Fallback based on resolution
          return resolution === "480p" ? 12 : 22;
     };

     // Check if user can generate (has subscription and enough credits)
     const canGenerate = () => {
          if (!user) return false;
          const requiredCredits = getRequiredCreditsSync(active);
          const hasEnoughCredits = (user.credit_balance || 0) >= requiredCredits;
          return hasEnoughCredits;
     };

     // Get button text and action
     const getButtonConfig = () => {
          if (isGenerating) return { text: "Generating...", action: handleGenerate };
          if (imageUploading || videoUploading) return { text: "Uploading...", action: handleGenerate };
          
          if (!user) return { text: "Generate", action: () => router.push("/signup") };
          
          const hasSubscription = !!user.plan_name;
          const requiredCredits = getRequiredCreditsSync(active);
          const hasEnoughCredits = (user.credit_balance || 0) >= requiredCredits;
          
          if (!hasEnoughCredits) {
               return { text: "Get More Credits", action: () => router.push("/upgrade") };
          }
          
          return { 
               text: `Generate (${requiredCredits})`, 
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

     // Auto-refresh jobs list periodically to catch new jobs and status updates
     useEffect(() => {
          if (!user) return;

          // Poll every 15 seconds (4 requests per minute, well under 60 limit)
          const jobsPollInterval = setInterval(() => {
               if (!rateLimited) {
                    loadPreviousJobs();
               }
          }, 15000);

          return () => clearInterval(jobsPollInterval);
     }, [user, rateLimited]);

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
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/wan-animate/jobs?limit=10`, {
                    headers: {
                         "Authorization": `Bearer ${token}`
                    }
               });

               // Handle rate limit errors
               if (response.status === 429) {
                    console.warn("Rate limit exceeded, pausing auto-refresh for 60 seconds");
                    setRateLimited(true);
                    setLoadingJobs(false); // Stop loading even on rate limit
                    // Resume after 60 seconds
                    setTimeout(() => {
                         setRateLimited(false);
                    }, 60000);
                    return;
               }

               const data = await response.json();

               console.log("Jobs response:", data);

               if (response.ok && data.jobs) {
                    console.log(`Loaded ${data.jobs.length} jobs:`, data.jobs);
                    
                    // Update both states together to prevent flash
                    setPreviousJobs(data.jobs);
                    setLoadingJobs(false);
                    setHasLoadedOnce(true);
                    
                    // Check status for jobs that are still pending/running but might be completed
                    // Only check the first few jobs to avoid too many requests
                    const jobsToCheck = data.jobs
                         .filter((job: any) => (job.status === "pending" || job.status === "running" || job.status === "processing" || (job.status === "completed" && !job.output_url)) && !job.output_url)
                         .slice(0, 3); // Only check up to 3 jobs at a time
                    
                    jobsToCheck.forEach((job: any) => {
                         // Only check if job was created more than 30 seconds ago (to avoid checking too early)
                         const jobCreated = new Date(job.created_at);
                         const now = new Date();
                         const secondsSinceCreation = (now.getTime() - jobCreated.getTime()) / 1000;
                         if (secondsSinceCreation > 30) {
                              // Trigger a status check for jobs that might be completed
                              pollJobStatus(job.job_id);
                         }
                    });
                    
                    // Update selected job if it exists in the new list
                    if (selectedJob) {
                         const updatedSelectedJob = data.jobs.find((job: any) => job.job_id === selectedJob.job_id);
                         if (updatedSelectedJob) {
                              setSelectedJob(updatedSelectedJob);
                              // If the selected job completed, update outputUrl
                              if (updatedSelectedJob.status === "completed" && updatedSelectedJob.output_url) {
                                   setOutputUrl(updatedSelectedJob.output_url);
                                   setJobStatus("completed");
                              } else if (updatedSelectedJob.status === "pending" || updatedSelectedJob.status === "running") {
                                   setJobStatus(updatedSelectedJob.status);
                              }
                         }
                    }
                    
                    // Show most recent job if available and no current selection
                    if (data.jobs.length > 0 && !selectedJob && !outputUrl && !isGenerating && !isPolling) {
                         const mostRecentJob = data.jobs[0]; // Jobs are already sorted by created_at desc
                         if (mostRecentJob.status === "completed" && mostRecentJob.output_url) {
                              setOutputUrl(mostRecentJob.output_url);
                              setSelectedJob(mostRecentJob);
                              setJobStatus("completed");
                         } else if (mostRecentJob.status === "pending" || mostRecentJob.status === "running" || mostRecentJob.status === "processing") {
                              // Set job info for pending/running jobs
                              setJobId(mostRecentJob.job_id);
                              setJobStatus(mostRecentJob.status);
                              setSelectedJob(mostRecentJob);
                              
                              // Restore job start time from localStorage if not set
                              if (!jobStartTime && mostRecentJob.created_at) {
                                   const storedStartTime = localStorage.getItem(`job_start_${mostRecentJob.job_id}`);
                                   if (storedStartTime) {
                                        setJobStartTime(parseInt(storedStartTime));
                                   } else {
                                        // Use job creation time as fallback
                                        const createdTime = new Date(mostRecentJob.created_at).getTime();
                                        setJobStartTime(createdTime);
                                        localStorage.setItem(`job_start_${mostRecentJob.job_id}`, createdTime.toString());
                                   }
                              }
                              
                              // Resume generating state if job is still pending/running
                              if ((mostRecentJob.status === "pending" || mostRecentJob.status === "running" || mostRecentJob.status === "processing") && !mostRecentJob.output_url) {
                                   if (!isGenerating) {
                                        setIsGenerating(true);
                                   }
                              }
                              
                              setIsPolling(true);
                              // Start polling if not already polling
                              pollJobStatus(mostRecentJob.job_id);
                         }
                    }
                    
                    // Resume generating state for current job if it's still pending/running
                    if (jobId) {
                         const currentJob = data.jobs.find((job: any) => job.job_id === jobId);
                         if (currentJob) {
                              // Restore job start time from localStorage if not set
                              if (!jobStartTime && currentJob.created_at) {
                                   const storedStartTime = localStorage.getItem(`job_start_${jobId}`);
                                   if (storedStartTime) {
                                        setJobStartTime(parseInt(storedStartTime));
                                   } else {
                                        // Use job creation time as fallback
                                        const createdTime = new Date(currentJob.created_at).getTime();
                                        setJobStartTime(createdTime);
                                        localStorage.setItem(`job_start_${jobId}`, createdTime.toString());
                                   }
                              }
                              
                              if ((currentJob.status === "pending" || currentJob.status === "running" || currentJob.status === "processing") && !currentJob.output_url) {
                                   // Resume generating state and polling only if not already generating
                                   if (!isGenerating) {
                                        setIsGenerating(true);
                                   }
                                   if (!isPolling) {
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
                                   // Clean up localStorage
                                   localStorage.removeItem(`job_start_${jobId}`);
                              } else if (currentJob.status === "failed") {
                                   // Job failed
                                   setError(currentJob.error || "Video generation failed. Please try changing your prompt or using a different photo.");
                                   setIsGenerating(false);
                                   setIsPolling(false);
                                   isSubmittingRef.current = false; // Reset ref
                                   // Clean up localStorage
                                   localStorage.removeItem(`job_start_${jobId}`);
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

     const uploadFileToBackblaze = async (file: File, type: "image" | "video") => {
          const token = getToken();
          if (!token) {
               router.push("/login");
               return null;
          }

          const formData = new FormData();
          formData.append("file", file);

          try {
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/storage/upload/wan-animate`, {
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
               console.error(`Error uploading ${type}:`, err);
               setError(`Failed to upload ${type}: ${err.message}`);
               return null;
          }
     };

     const handleImageSelect = async (file: File) => {
          if (!file.type.startsWith("image/")) {
               setError("Please select an image file");
               return;
          }

          // Clear old image data IMMEDIATELY before setting new one
          // This ensures the old Backblaze URL is not used
          const oldUrl = imageUrlRef.current;
          console.log("🗑️ Clearing old image. Previous URL was:", oldUrl);
          
          // Clear ref FIRST (synchronous, immediate) - this prevents any old URL from being used
          imageUrlRef.current = null;
          imageUploadTimestampRef.current = 0; // Reset timestamp
          
          // Then clear state (triggers useEffect to sync)
          setImageFile(null);
          setImagePreview(null);
          setImageUrl(null);
          setError(null);
          
          console.log("✅ Old image cleared. Ref is now:", imageUrlRef.current);

          // Set new file (but DON'T upload yet - wait for Generate button)
          setImageFile(file);

          // Create preview
          const reader = new FileReader();
          reader.onload = (e) => {
               setImagePreview(e.target?.result as string);
          };
          reader.readAsDataURL(file);
          
          console.log("✅ Image file selected and preview created. Upload will happen when Generate is clicked.");
     };

     const handleVideoSelect = async (file: File) => {
          if (!file.type.startsWith("video/")) {
               setError("Please select a video file");
               return;
          }

          // Clear old video data IMMEDIATELY before setting new one
          // This ensures the old Backblaze URL is not used
          const oldUrl = videoUrlRef.current;
          console.log("🗑️ Clearing old video. Previous URL was:", oldUrl);
          
          // Clear ref FIRST (synchronous, immediate) - this prevents any old URL from being used
          videoUrlRef.current = null;
          videoUploadTimestampRef.current = 0; // Reset timestamp
          
          // Then clear state (triggers useEffect to sync)
          setVideoFile(null);
          setVideoPreview(null);
          setVideoUrl(null);
          setError(null);
          
          console.log("✅ Old video cleared. Ref is now:", videoUrlRef.current);

          // Set new file (but DON'T upload yet - wait for Generate button)
          setVideoFile(file);

          // Create preview
          const reader = new FileReader();
          reader.onload = (e) => {
               setVideoPreview(e.target?.result as string);
          };
          reader.readAsDataURL(file);
          
          console.log("✅ Video file selected and preview created. Upload will happen when Generate is clicked.");
     };

     const handleGenerate = async () => {
          // Prevent double submission
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

          if (!videoFile && !videoUrl) {
               setError("Please select a video first");
               return;
          }

          // Set ref immediately to prevent double submission
          isSubmittingRef.current = true;
          setError(null);
          setOutputUrl(null);
          setJobStatus(null);
          
          // Save current file data for upload, but keep previews visible
          const currentImageFile = imageFile;
          const currentVideoFile = videoFile;
          const currentImageUrl = imageUrlRef.current || imageUrl;
          const currentVideoUrl = videoUrlRef.current || videoUrl;
          
          // Clear only the file objects to allow new uploads, but keep previews and URLs visible
          setImageFile(null);
          setVideoFile(null);
          
          // Reset the file input fields to allow reselecting the same files
          if (imageInputRef.current) {
               imageInputRef.current.value = '';
          }
          if (videoInputRef.current) {
               videoInputRef.current.value = '';
          }

          try {
               // Upload both files in parallel if needed
               let finalImageUrl = currentImageUrl;
               let finalVideoUrl = currentVideoUrl;
               
               // Check if we need to upload either file
               const needImageUpload = currentImageFile && !finalImageUrl;
               const needVideoUpload = currentVideoFile && !finalVideoUrl;
               
               if (needImageUpload || needVideoUpload) {
                    console.log("📤 Uploading files to Backblaze before generation...");
                    setImageUploading(!!needImageUpload);
                    setVideoUploading(!!needVideoUpload);
                    
                    try {
                         // Upload both files in parallel for faster uploads
                         const uploadPromises = [];
                         
                         if (needImageUpload) {
                              const imageUploadPromise = uploadFileToBackblaze(currentImageFile, "image")
                                   .then((url) => {
                                        if (url) {
                                             const uploadStartTime = Date.now();
                                             imageUrlRef.current = url;
                                             imageUploadTimestampRef.current = uploadStartTime;
                                             setImageUrl(url);
                                             console.log("✅ Image uploaded to Backblaze:", url);
                                             return { type: "image" as const, url };
                                        } else {
                                             throw new Error("Failed to upload image to Backblaze");
                                        }
                                   })
                                   .catch((error) => {
                                        console.error("❌ Image upload failed:", error);
                                        throw new Error(`Failed to upload image: ${error.message || "Unknown error"}`);
                                   });
                              uploadPromises.push(imageUploadPromise);
                         }
                         
                         if (needVideoUpload) {
                              const videoUploadPromise = uploadFileToBackblaze(currentVideoFile, "video")
                                   .then((url) => {
                                        if (url) {
                                             const uploadStartTime = Date.now();
                                             videoUrlRef.current = url;
                                             videoUploadTimestampRef.current = uploadStartTime;
                                             setVideoUrl(url);
                                             console.log("✅ Video uploaded to Backblaze:", url);
                                             return { type: "video" as const, url };
                                        } else {
                                             throw new Error("Failed to upload video to Backblaze");
                                        }
                                   })
                                   .catch((error) => {
                                        console.error("❌ Video upload failed:", error);
                                        throw new Error(`Failed to upload video: ${error.message || "Unknown error"}`);
                                   });
                              uploadPromises.push(videoUploadPromise);
                         }
                         
                         // Wait for all uploads to complete in parallel (use allSettled so one failure doesn't stop the other)
                         const uploadResults = await Promise.allSettled(uploadPromises);
                         
                         // Check results and update URLs
                         const uploadErrors: string[] = [];
                         
                         for (const result of uploadResults) {
                              if (result.status === "fulfilled") {
                                   if (result.value.type === "image") {
                                        finalImageUrl = result.value.url;
                                   } else if (result.value.type === "video") {
                                        finalVideoUrl = result.value.url;
                                   }
                              } else {
                                   // One of the uploads failed
                                   const errorMsg = result.reason?.message || "Unknown error";
                                   uploadErrors.push(errorMsg);
                                   console.error("❌ Upload error:", result.reason);
                              }
                         }
                         
                         // If any upload failed, throw an error with details
                         if (uploadErrors.length > 0) {
                              throw new Error(`Upload failed: ${uploadErrors.join("; ")}`);
                         }
                         
                         // Verify both required files are available
                         if (needImageUpload && !finalImageUrl) {
                              throw new Error("Image upload failed - no URL received");
                         }
                         if (needVideoUpload && !finalVideoUrl) {
                              throw new Error("Video upload failed - no URL received");
                         }
                    } catch (uploadError: any) {
                         console.error("❌ Upload failed:", uploadError);
                         throw uploadError;
                    } finally {
                         setImageUploading(false);
                         setVideoUploading(false);
                    }
               }
               
               if (!finalImageUrl || !finalVideoUrl) {
                    throw new Error("No image or video URL available. Please select both an image and a video first.");
               }
               
               // Now set generating state after uploads are complete
               setIsGenerating(true);
               
               console.log("🚀 Generating video...");
               console.log("🚀 Using image URL:", finalImageUrl);
               console.log("🚀 Using video URL:", finalVideoUrl);

               // Get auth token
               const token = getToken();
               if (!token) {
                    router.push("/login");
                    return;
               }

               console.log("Submitting job with token:", token ? "Token present" : "No token");

               // Submit job with URLs (files already uploaded)
               const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/wan-animate/submit`, {
                    method: "POST",
                    headers: {
                         "Authorization": `Bearer ${token}`,
                         "Content-Type": "application/json"
                    },
                    credentials: "include",
                    body: JSON.stringify({
                         image_url: finalImageUrl, // Use the uploaded image URL
                         video_url: finalVideoUrl, // Use the uploaded video URL
                         mode: mode,
                         resolution: active,
                         prompt: prompt || undefined,
                         seed: "-1"
                    })
               });

               const data = await response.json();

               if (!response.ok) {
                    // If 401, token might be expired - try to refresh or redirect to login
                    if (response.status === 401) {
                         console.error("Authentication failed:", data);
                         setError("Your session has expired. Please log in again.");
                         // Clear token and redirect after a short delay
                         setTimeout(() => {
                              router.push("/login");
                         }, 2000);
                         return;
                    }
                    throw new Error(data.detail || "Failed to submit job");
               }

               // Job submitted successfully
               console.log("Job submitted:", data);
               setJobId(data.job_id);
               setJobStatus("pending");
               
               // Store job start time for progress calculation (persists across refreshes)
               const startTime = Date.now();
               setJobStartTime(startTime);
               // Store in localStorage for persistence across refreshes
               if (data.job_id) {
                    localStorage.setItem(`job_start_${data.job_id}`, startTime.toString());
               }
               
               setIsPolling(true);
               // Reload jobs list to show the new job immediately
               loadPreviousJobs();
               // Start polling for job status
               pollJobStatus(data.job_id);

          } catch (err: any) {
               console.error("Error submitting job:", err);
               setError(err.message || "Failed to submit job. Please try again.");
               setIsGenerating(false);
               setImageUploading(false);
               setVideoUploading(false);
               isSubmittingRef.current = false; // Reset ref on error
          }
     };

     const pollJobStatus = async (jobId: string) => {
          const token = getToken();
          if (!token) {
               setIsGenerating(false);
               return;
          }

          let pollInterval: NodeJS.Timeout | null = null;

          const poll = async () => {
               try {
                    const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/wan-animate/status/${jobId}`, {
                         headers: {
                              "Authorization": `Bearer ${token}`
                         }
                    });

                    const data = await response.json();

                    if (!response.ok) {
                         throw new Error(data.detail || "Failed to get job status");
                    }

                    setJobStatus(data.status);

                    if (data.status === "completed" && data.output_url) {
                         setOutputUrl(data.output_url);
                         setJobStatus("completed");
                         setProgress(100);
                         setIsGenerating(false);
                         setIsPolling(false);
                         if (pollInterval) clearInterval(pollInterval);
                         console.log("Job completed:", data.output_url);
                         // Clean up localStorage
                         localStorage.removeItem(`job_start_${jobId}`);
                         // Reload previous jobs to include the new one
                         loadPreviousJobs();
                    } else if (data.status === "failed") {
                         setError(data.error || "Job failed");
                         setIsGenerating(false);
                         setIsPolling(false);
                         if (pollInterval) clearInterval(pollInterval);
                         // Clean up localStorage
                         localStorage.removeItem(`job_start_${jobId}`);
                    } else if (data.status === "running" || data.status === "pending") {
                         setJobStatus(data.status);
                    }
               } catch (err: any) {
                    console.error("Error polling job status:", err);
                    if (pollInterval) clearInterval(pollInterval);
                    setIsGenerating(false);
                    setIsPolling(false);
               }
          };

          // Poll immediately first time
          poll();

          // Then poll every 3 seconds
          pollInterval = setInterval(poll, 3000);

          // Clear interval after 5 minutes (timeout)
          setTimeout(() => {
               if (pollInterval) clearInterval(pollInterval);
               if (jobStatus !== "completed" && jobStatus !== "failed") {
                    setError("Job timed out. Please check back later.");
                    setIsGenerating(false);
                    setIsPolling(false);
               }
          }, 300000); // 5 minutes
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
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Input Image</h3>
                                   <input
                                        type="file"
                                        ref={imageInputRef}
                                        accept="image/*"
                                        className="hidden"
                                        onChange={(e) => {
                                             const file = e.target.files?.[0];
                                             if (file) {
                                                  handleImageSelect(file);
                                             }
                                        }}
                                   />
                                   <div 
                                        ref={imageDropRef}
                                        onClick={() => imageInputRef.current?.click()}
                                        onDragOver={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (imageDropRef.current) {
                                                  imageDropRef.current.classList.add("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDragLeave={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (imageDropRef.current) {
                                                  imageDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDrop={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (imageDropRef.current) {
                                                  imageDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                             const file = e.dataTransfer.files[0];
                                             if (file && file.type.startsWith("image/")) {
                                                  handleImageSelect(file);
                                             } else {
                                                  setError("Please drop an image file");
                                             }
                                        }}
                                        className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-6 text-center cursor-pointer hover:border-blue-1100 transition-colors relative"
                                   >
                                        {imageUploading && (
                                             <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center z-20">
                                                  <div className="text-xs text-white">Uploading...</div>
                                             </div>
                                        )}
                                        {imagePreview ? (
                                             <div className="relative">
                                                  <img src={imagePreview} alt="Preview" className="w-full h-32 object-cover rounded-lg mb-2" />
                                                  {imageUrl && (
                                                       <div className="text-[10px] text-green-400">✓ Uploaded</div>
                                                  )}
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
                                                  <p className="text-[10px] text-white/40 mt-1">or drag and drop</p>
                                             </>
                                        )}
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Input Video</h3>
                                   <input
                                        type="file"
                                        ref={videoInputRef}
                                        accept="video/*"
                                        className="hidden"
                                        onChange={(e) => {
                                             const file = e.target.files?.[0];
                                             if (file) {
                                                  handleVideoSelect(file);
                                             }
                                        }}
                                   />
                                   <div 
                                        ref={videoDropRef}
                                        onClick={() => videoInputRef.current?.click()}
                                        onDragOver={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (videoDropRef.current) {
                                                  videoDropRef.current.classList.add("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDragLeave={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (videoDropRef.current) {
                                                  videoDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                        }}
                                        onDrop={(e) => {
                                             e.preventDefault();
                                             e.stopPropagation();
                                             if (videoDropRef.current) {
                                                  videoDropRef.current.classList.remove("border-blue-1100", "bg-blue-1100/10");
                                             }
                                             const file = e.dataTransfer.files[0];
                                             if (file && file.type.startsWith("video/")) {
                                                  handleVideoSelect(file);
                                             } else {
                                                  setError("Please drop a video file");
                                             }
                                        }}
                                        className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-6 text-center cursor-pointer hover:border-blue-1100 transition-colors relative"
                                   >
                                        {videoUploading && (
                                             <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center z-20">
                                                  <div className="text-xs text-white">Uploading...</div>
                                             </div>
                                        )}
                                        {videoPreview ? (
                                             <div className="relative">
                                                  <video src={videoPreview} className="w-full h-32 object-cover rounded-lg mb-2" controls />
                                                  {videoUrl && (
                                                       <div className="text-[10px] text-green-400">✓ Uploaded</div>
                                                  )}
                                             </div>
                                        ) : (
                                             <>
                                                  <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400">
                                                       <img src="/images/VideoCamera.svg" alt="" />
                                                       <div className="bg-gray-1500/[30%] flex items-center backdrop-blur-[8px] justify-center w-4 h-4 rounded-full absolute -top-2 -right-2">
                                                            <img src="/images/Plus.svg" alt="" />
                                                       </div>
                                                  </div>
                                                  <h6 className="text-xs font-medium leading-[120%] text-white mt-2.5 mb-1">Upload a Video Motion Template</h6>
                                                  <p className="text-xs max-w-[177px] mx-auto font-normal leading-[120%] text-white/60">Choose or upload a short clip to drive your animation.</p>
                                                  <p className="text-[10px] text-white/40 mt-1">or drag and drop</p>
                                             </>
                                        )}
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Prompt</h3>
                                   <textarea
                                        className="w-full h-32 rounded-lg border border-gray-1100 bg-black-1000 p-3 text-xs text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                        placeholder="Describe the animation you want to generate..."
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                   />
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Mode</h3>
                                   <div className="grid grid-cols-2 gap-1">
                                        <button
                                             type="button"
                                             onClick={() => setMode("animate")}
                                             className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center gap-1 w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
            ${mode === "animate" ? "bg-gray-1100/30! border-blue-1100!" : ""} 
          `}
                                        >
                                             Animate
                                        </button>
                                        <button
                                             type="button"
                                             onClick={() => setMode("replace")}
                                             className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center gap-1 w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
            ${mode === "replace" ? "bg-gray-1100/30! border-blue-1100!" : ""} 
          `}
                                        >
                                             Replace
                                        </button>
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Resolution</h3>
                                   <div className="grid grid-cols-2 gap-1">
                                        {options.map((opt) => {
                                             const credits = getRequiredCreditsSync(opt);
                                             return (
                                                  <button
                                                       key={opt}
                                                       type="button"
                                                       onClick={() => setActive(opt)}
                                                       className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center gap-1 w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
            ${active === opt ? "bg-gray-1100/30! border-blue-1100!" : ""} 
          `}
                                                  >
                                                       {opt} ({credits})
                                                  </button>
                                             );
                                        })}
                                   </div>
                              </div>
                         </div>
                         <div className="text-center">
                              {error && (
                                   <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg">
                                        <p className="text-xs text-red-400">{error}</p>
                                   </div>
                              )}
                              {(() => {
                                   const buttonConfig = getButtonConfig();
                                   const isGenerateAction = buttonConfig.action === handleGenerate;
                                   const isDisabled = isGenerateAction && ((!imageFile && !imageUrl) || (!videoFile && !videoUrl) || isGenerating || imageUploading || videoUploading || isSubmittingRef.current);
                                   
                                   return (
                                        <button 
                                             onClick={buttonConfig.action}
                                             disabled={isDisabled}
                                             className={clsx(
                                                  "md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl transition-all duration-300 relative overflow-hidden",
                                                  isDisabled 
                                                       ? "cursor-not-allowed" 
                                                       : "hover:shadow-7xl"
                                             )}
                                        >
                                             {(isGenerating || imageUploading || videoUploading) ? (
                                                  <>
                                                       <span className="relative z-10">{buttonConfig.text}</span>
                                                       <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                                                  </>
                                             ) : (
                                                  buttonConfig.text
                                             )}
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
                                                       onSelectJob={(job) => {
                                                            setSelectedJob(job);
                                                            // Restore settings if retrying a failed job
                                                            if (job && (job.status === 'failed' || job.status === 'completed')) {
                                                                 if (job.settings) {
                                                                      // Restore prompt
                                                                      if (job.settings.prompt || job.input_prompt) {
                                                                           setPrompt(job.settings.prompt || job.input_prompt);
                                                                      }
                                                                      // Restore resolution
                                                                      if (job.settings.resolution) {
                                                                           setActive(job.settings.resolution);
                                                                      }
                                                                      // Restore mode
                                                                      if (job.settings.mode) {
                                                                           setMode(job.settings.mode);
                                                                      }
                                                                      // Restore image/video previews if available
                                                                      if (job.settings.image_url && !imagePreview) {
                                                                           setImagePreview(job.settings.image_url);
                                                                           setImageUrl(job.settings.image_url);
                                                                           imageUrlRef.current = job.settings.image_url;
                                                                      }
                                                                      if (job.settings.video_url && !videoPreview) {
                                                                           setVideoPreview(job.settings.video_url);
                                                                           setVideoUrl(job.settings.video_url);
                                                                           videoUrlRef.current = job.settings.video_url;
                                                                      }
                                                                      
                                                                      // Open sidebar on mobile
                                                                      if (window.innerWidth < 1024) {
                                                                           setSidebarOpen(true);
                                                                      }
                                                                 }
                                                            }
                                                       }}
                                                  />
                                             </div>
                                        ) : previousJobs.length > 0 || outputUrl || (isGenerating && imagePreview) || jobId ? (
                                             // Show video gallery
                                             <div className="w-full max-w-[1320px] mx-auto">
                                                  {/* Mobile-only Generate button */}
                                                  <div className="md:hidden block mb-6 px-5">
                                                       <div className="text-center mb-6">
                                                            <div className="flex gap-2 items-center justify-center mb-2">
                                                                 <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">HOT</span>
                                                                 <h6 className="text-sm font-normal leading-[120%] text-gradient">Character Swap</h6>
                                                            </div>
                                                            <h2 className="text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Swap Any Character Instantly</h2>
                                                            <p className="text-sm font-medium leading-[120%] text-white/60 mb-6">Access Sora, Veo 3, Kling, Minimax & more. Replace characters in any video with AI.</p>
                                                            <button 
                                                                 onClick={() => user ? setSidebarOpen(true) : router.push("/signup")} 
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
                                                                 if (job.settings) {
                                                                      // Restore prompt
                                                                      if (job.settings.prompt || job.input_prompt) {
                                                                           setPrompt(job.settings.prompt || job.input_prompt);
                                                                      }
                                                                      // Restore resolution
                                                                      if (job.settings.resolution) {
                                                                           setActive(job.settings.resolution);
                                                                      }
                                                                      // Restore mode
                                                                      if (job.settings.mode) {
                                                                           setMode(job.settings.mode);
                                                                      }
                                                                      // Restore image/video previews if available
                                                                      if (job.settings.image_url && !imagePreview) {
                                                                           setImagePreview(job.settings.image_url);
                                                                           setImageUrl(job.settings.image_url);
                                                                           imageUrlRef.current = job.settings.image_url;
                                                                      }
                                                                      if (job.settings.video_url && !videoPreview) {
                                                                           setVideoPreview(job.settings.video_url);
                                                                           setVideoUrl(job.settings.video_url);
                                                                           videoUrlRef.current = job.settings.video_url;
                                                                      }
                                                                      
                                                                      // Open sidebar on mobile
                                                                      if (window.innerWidth < 1024) {
                                                                           setSidebarOpen(true);
                                                                      }
                                                                 }
                                                            }
                                                       }}
                                                  />
                                             </div>
                                        ) : (
                              // Initial state - show instructions
                              <>
                                   <div className="text-center mb-6 pt-4 md:pt-0">
                                        <div className="flex gap-2 items-center justify-center">
                                             <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">HOT</span>
                                             <h6 className="text-sm font-normal leading-[120%] text-gradient">Character Swap</h6>
                                        </div>
                                        <h2 className="md:text-5xl text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Swap Any Character Instantly</h2>
                                        <p className="md:text-base text-sm font-medium leading-[120%] text-white/60">Access Sora, Veo 3, Kling, Minimax & more. Replace characters in any video with AI.</p>
                                        <div className="md:hidden block mt-12">
                                             <button  
                                                  onClick={() => user ? setSidebarOpen(true) : router.push("/signup")} 
                                                  className="md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300" 
                                             >
                                                  Generate
                                             </button>
                                        </div>
                                        <div className="flex items-center mt-20 w-fit mx-auto gap-2 py-2 px-3 rounded-full backdrop-blur-[4px] border border-gray-1700 tag-bg">
                                             <img src="/images/MagicWand2.svg" alt="" />
                                             <h6 className="text-sm font-normal leading-[120%] text-gradient">Generate in 3 easy steps</h6>
                                        </div>
                                   </div>
                                   <div className="grid xl:grid-cols-3 md:grid-cols-2 md:max-w-[980px] max-w-full mx-auto gap-4">
                                        <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                             <div className="w-full aspect-[4/3] overflow-hidden rounded-xl">
                                                  <img src="/images/wan/Upload-image.webp" alt="" className="w-full h-full object-cover" />
                                             </div>
                                             <div className="mt-2 py-4 px-2">
                                                  <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                                       <span className="text-white/60">01</span>    Upload an Image
                                                  </h4>
                                                  <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                                       Choose a photo of you or any character
                                                  </p>
                                             </div>
                                        </div>
                                        <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                             <div className="w-full aspect-[4/3] overflow-hidden rounded-xl relative">
                                                  <video
                                                       ref={uploadVideoRef}
                                                       src="/images/wan/Upload-Video-Template.mp4?v=2"
                                                       autoPlay
                                                       muted
                                                       playsInline
                                                       loop
                                                       preload="auto"
                                                       crossOrigin="anonymous"
                                                       className="w-full h-full object-cover"
                                                       style={{ pointerEvents: 'none' }}
                                                       onError={(e) => {
                                                            console.error('Video upload template error:', e);
                                                       }}
                                                       onLoadedData={() => {
                                                            console.log('Video upload template loaded');
                                                            uploadVideoRef.current?.play().catch(err => console.error('Play failed:', err));
                                                       }}
                                                  />
                                             </div>
                                             <div className="mt-2 py-4 px-2">
                                                  <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                                       <span className="text-white/60">02</span>  Upload a Video Template
                                                  </h4>
                                                  <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                                       Use a video to animate your image.
                                                  </p>
                                             </div>
                                        </div>
                                        <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                             <div className="w-full aspect-[4/3] overflow-hidden rounded-xl relative">
                                                  <video
                                                       ref={bringToLifeVideoRef}
                                                       src="/images/wan/Bring-to-Life.mp4?v=2"
                                                       autoPlay
                                                       muted
                                                       playsInline
                                                       loop
                                                       preload="auto"
                                                       crossOrigin="anonymous"
                                                       className="w-full h-full object-cover"
                                                       style={{ pointerEvents: 'none' }}
                                                       onError={(e) => {
                                                            console.error('Video bring to life error:', e);
                                                       }}
                                                       onLoadedData={() => {
                                                            console.log('Video bring to life loaded');
                                                            bringToLifeVideoRef.current?.play().catch(err => console.error('Play failed:', err));
                                                       }}
                                                  />
                                             </div>
                                             <div className="mt-2 py-4 px-2">
                                                  <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                                       <span className="text-white/60">03</span> Bring It to Life
                                                  </h4>
                                                  <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                                       Become the character in the scene
                                                  </p>
                                             </div>
                                        </div>
                                   </div>
                              </>
                         )}
                         
                         {/* Generating indicator - shows on both pages */}
                         {isGenerating && !outputUrl && (
                              <div className="fixed bottom-8 right-8 z-50 bg-black-1000 border border-gray-1100 p-4 rounded-xl shadow-2xl w-[320px] animate-in slide-in-from-bottom-4">
                                   <div className="flex items-center gap-4 mb-3">
                                        <div className="w-12 h-12 rounded-lg overflow-hidden relative flex-shrink-0">
                                             <img src={imagePreview || ""} className="w-full h-full object-cover opacity-50" alt="" />
                                             <div className="absolute inset-0 flex items-center justify-center">
                                                  <div className="w-6 h-6 border-2 border-blue-1100 border-t-transparent rounded-full animate-spin"></div>
                                             </div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                             <h4 className="text-sm font-medium text-white">Generating Video...</h4>
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

export default page
