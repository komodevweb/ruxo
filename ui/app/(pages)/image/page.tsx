"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import clsx from 'clsx';
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/react';
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import { allImages } from "../../lib/gallery-images";

export default function ImagePage() {
     const { user, loading: authLoading } = useAuth();
     const router = useRouter();
     const [prompt, setPrompt] = useState("");
     const [selectedModel, setSelectedModel] = useState<any>(null);
     const [selectedRatio, setSelectedRatio] = useState<string>("1:1");
     const [selectedResolution, setSelectedResolution] = useState<string>("1k");
     const [selectedOutputFormat, setSelectedOutputFormat] = useState<string>("jpeg");
     const [isGenerating, setIsGenerating] = useState(false);
     const [outputUrl, setOutputUrl] = useState<string | null>(null);
     const [jobId, setJobId] = useState<string | null>(null);
     const [error, setError] = useState<string | null>(null);
     const [activeTab, setActiveTab] = useState("explore"); // explore | creations
     const [mode, setMode] = useState("text-to-image"); // text-to-image | image-to-image
     const [allModels, setAllModels] = useState<any[]>([]); // Store all models (unfiltered)
     const [models, setModels] = useState<any[]>([]); // Filtered models based on mode
     const [loadingModels, setLoadingModels] = useState(true);
     const [creditCache, setCreditCache] = useState<Map<string, number>>(new Map());
     const [imageFile, setImageFile] = useState<File | null>(null);
     const [imagePreview, setImagePreview] = useState<string | null>(null);
     const [imageUrl, setImageUrl] = useState<string | null>(null);
     const [imageUploading, setImageUploading] = useState(false);
     const imageUrlRef = useRef<string | null>(null);
     const imageUploadTimestampRef = useRef<number>(0);
     const imageDropRef = useRef<HTMLLabelElement>(null);
     const [myCreations, setMyCreations] = useState<any[]>([]);
     const [loadingCreations, setLoadingCreations] = useState(false);
     const [hasLoadedCreationsOnce, setHasLoadedCreationsOnce] = useState(false);
     const [selectedImageOverlay, setSelectedImageOverlay] = useState<string | null>(null);

     // Get available aspect ratios based on selected model
     const getAvailableAspectRatios = () => {
          if (!selectedModel) return [];
          return (selectedModel.supported_aspect_ratios || []).map((ratio: string) => ({
               id: ratio,
               name: ratio
          }));
     };

     // Get available resolutions based on selected model
     const getAvailableResolutions = () => {
          if (!selectedModel) return [];
          return (selectedModel.supported_resolutions || []).map((res: string) => ({
               id: res,
               name: res
          }));
     };

     // Get available output formats based on selected model
     const getAvailableOutputFormats = () => {
          if (!selectedModel) return [];
          return (selectedModel.supported_output_formats || []).map((format: string) => ({
               id: format,
               name: format.toUpperCase()
          }));
     };

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

     // Initialize gallery images with aspect ratios
     const MAX_EXPLORE_IMAGES = 18;
     const [galleryImages, setGalleryImages] = useState<Array<{ id: number; src: string; type: string; aspect: string }>>(() => {
          // Fixed initial state for SSR
          return allImages.slice(0, MAX_EXPLORE_IMAGES).map((src, index) => ({
               id: index + 1,
               src,
               type: "image",
               aspect: aspectRatios[index % aspectRatios.length],
          }));
     });

     useEffect(() => {
          // Shuffle images with random aspect ratios on mount - use requestIdleCallback for better performance
          const shuffleAndSetImages = () => {
               const shuffledImages = shuffleArray(allImages);
               const shuffled = shuffledImages.slice(0, MAX_EXPLORE_IMAGES).map((src, index) => ({
                    id: index + 1,
                    src,
                    type: "image",
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

     // Fetch required credits from backend
     const getRequiredCredits = async (modelId: string, resolution: string): Promise<number> => {
          if (!modelId || !resolution) return 0;
          
          const cacheKey = `${modelId}-${resolution}`;
          
          // Check cache first
          if (creditCache.has(cacheKey)) {
               return creditCache.get(cacheKey)!;
          }
          
          try {
               const apiUrl = process.env.NEXT_PUBLIC_API_V1_URL;
               if (!apiUrl) {
                    console.error("NEXT_PUBLIC_API_V1_URL is not defined");
                    return 0;
               }
               
               const token = getToken();
               if (!token) return 0;
               
               const response = await fetch(
                    `${apiUrl}/image/calculate-credits?model_id=${encodeURIComponent(modelId)}&resolution=${encodeURIComponent(resolution)}`,
                    {
                         method: "GET",
                         headers: {
                              "Authorization": `Bearer ${token}`,
                              "Content-Type": "application/json",
                         },
                    }
               );
               
               if (response.ok) {
                    const data = await response.json();
                    const credits = data.credits || 0;
                    // Cache the result
                    setCreditCache(prev => new Map(prev).set(cacheKey, credits));
                    return credits;
               } else {
                    console.error("Failed to calculate credits:", response.statusText);
               }
          } catch (error: any) {
               console.error("Error fetching credit cost:", error);
               // Don't show error to user for credit calculation failures, just return 0
          }
          
          return 0;
     };
     
     // Synchronous version for immediate display (uses cached value or returns 0)
     const getRequiredCreditsSync = (modelId: string, resolution: string): number => {
          if (!modelId || !resolution) return 0;
          const cacheKey = `${modelId}-${resolution}`;
          return creditCache.get(cacheKey) || 0;
     };

     // Upload file to Backblaze
     const uploadFileToBackblaze = async (file: File) => {
          const token = getToken();
          if (!token) {
               router.push("/login");
               return null;
          }

          const formData = new FormData();
          formData.append("file", file);

          try {
               const endpoint = `${process.env.NEXT_PUBLIC_API_V1_URL}/storage/upload/image-to-image`;
               
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
               console.error("Error uploading image:", err);
               setError(`Failed to upload image: ${err.message}`);
               return null;
          }
     };

     // Handle image file selection
     const handleImageSelect = useCallback(async (file: File) => {
          if (!file.type.startsWith("image/")) {
               setError("Please select an image file (JPG, PNG, etc.)");
               return;
          }

          // Check file size (10 MB limit)
          if (file.size > 10 * 1024 * 1024) {
               setError("Image file must be 10 MB or less");
               return;
          }

          // Clear old image data IMMEDIATELY before setting new one
          const oldUrl = imageUrlRef.current;
          console.log("🗑️ Clearing old image. Previous URL was:", oldUrl);
          
          // Clear ref FIRST (synchronous, immediate)
          imageUrlRef.current = null;
          imageUploadTimestampRef.current = 0;
          
          // Then clear state
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
     }, []);

     // Load models from backend (works for both logged in and logged out users)
     const loadModels = async () => {
          try {
               setLoadingModels(true);
               const apiUrl = process.env.NEXT_PUBLIC_API_V1_URL;
               if (!apiUrl) {
                    console.error("NEXT_PUBLIC_API_V1_URL is not defined");
                    setError("API URL is not configured. Please check your environment variables.");
                    return;
               }
               
               const token = getToken();
               
               const headers: HeadersInit = {
                    "Content-Type": "application/json",
               };
               
               // Only add Authorization header if token exists
               if (token) {
                    headers["Authorization"] = `Bearer ${token}`;
               }
               
               const response = await fetch(
                    `${apiUrl}/image/models`,
                    {
                         method: "GET",
                         headers,
                    }
               );
               
               if (response.ok) {
                    const data = await response.json();
                    const fetchedModels = data.models || [];
                    // Store all models (unfiltered)
                    setAllModels(fetchedModels);
                    // Filter models based on current mode
                    const filteredModels = mode === "image-to-image" 
                         ? fetchedModels.filter((m: any) => m.supports_image_to_image)
                         : fetchedModels.filter((m: any) => {
                              // In text-to-image mode: exclude edit-only models
                              // Models with "edit" in their id or display_name should only appear in image-to-image mode
                              const isEditModel = m.id?.includes("edit") || m.id?.includes("-edit") || 
                                                  m.display_name?.toLowerCase().includes("edit");
                              // Exclude models that only support image-to-image (edit-only models)
                              return !isEditModel;
                         });
                    setModels(filteredModels);
                    if (filteredModels.length > 0 && !selectedModel) {
                         // Set default model based on mode
                         const defaultModel = mode === "image-to-image"
                              ? filteredModels.find((m: any) => m.id === "google-nano-banana-pro-edit") || filteredModels[0]
                              : filteredModels[0];
                         setSelectedModel(defaultModel);
                    } else if (filteredModels.length > 0 && selectedModel && !filteredModels.find((m: any) => m.id === selectedModel.id)) {
                         // If current model doesn't support the mode, switch to preferred default
                         const defaultModel = mode === "image-to-image"
                              ? filteredModels.find((m: any) => m.id === "google-nano-banana-pro-edit") || filteredModels[0]
                              : filteredModels[0];
                         setSelectedModel(defaultModel);
                    }
               } else {
                    console.error("Failed to load models:", response.statusText);
                    setError(`Failed to load models: ${response.statusText}`);
               }
          } catch (err: any) {
               console.error("Error loading models:", err);
               // Only set error if it's a network error, not if it's just a missing API URL
               if (err.message && !err.message.includes("NEXT_PUBLIC_API_V1_URL")) {
                    setError(`Failed to load models: ${err.message || "Network error"}`);
               }
          } finally {
               setLoadingModels(false);
          }
     };

     // Load models on initial mount
     useEffect(() => {
          loadModels();
     }, []);

     // Filter models when mode changes (without showing loading)
     useEffect(() => {
          if (allModels.length > 0) {
               // Filter all models based on mode (no API call, no loading state)
               const filteredModels = mode === "image-to-image" 
                    ? allModels.filter((m: any) => m.supports_image_to_image)
                    : allModels.filter((m: any) => {
                         // In text-to-image mode: exclude edit-only models
                         // Models with "edit" in their id or display_name should only appear in image-to-image mode
                         const isEditModel = m.id?.includes("edit") || m.id?.includes("-edit") || 
                                             m.display_name?.toLowerCase().includes("edit");
                         // Exclude models that only support image-to-image (edit-only models)
                         return !isEditModel;
                    });
               
               setModels(filteredModels);
               if (filteredModels.length > 0 && selectedModel && !filteredModels.find((m: any) => m.id === selectedModel.id)) {
                    // If current model doesn't support the mode, switch to preferred default
                    const defaultModel = mode === "image-to-image"
                         ? filteredModels.find((m: any) => m.id === "google-nano-banana-pro-edit") || filteredModels[0]
                         : filteredModels[0];
                    setSelectedModel(defaultModel);
               }
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [mode, allModels]);

     // Sync imageUrlRef with imageUrl state
     useEffect(() => {
          imageUrlRef.current = imageUrl;
     }, [imageUrl]);

     // Update default values when model changes
     useEffect(() => {
          if (selectedModel) {
               if (selectedModel.default_aspect_ratio) {
                    setSelectedRatio(selectedModel.default_aspect_ratio);
               }
               if (selectedModel.default_resolution) {
                    setSelectedResolution(selectedModel.default_resolution);
               }
               if (selectedModel.default_output_format) {
                    setSelectedOutputFormat(selectedModel.default_output_format);
               }
          }
     }, [selectedModel]);

     // Pre-fetch credit costs when model or resolution changes
     useEffect(() => {
          if (selectedModel && selectedResolution) {
               const modelId = selectedModel.id;
               const cacheKey = `${modelId}-${selectedResolution}`;
               
               // Only fetch if not already cached
               if (!creditCache.has(cacheKey)) {
                    getRequiredCredits(modelId, selectedResolution).catch(console.error);
               }
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [selectedModel, selectedResolution]);

     // Load user's creations
     const loadMyCreations = async () => {
          const token = getToken();
          if (!token || !user) {
               setMyCreations([]);
               setLoadingCreations(false);
               setHasLoadedCreationsOnce(false);
               return;
          }

          try {
               setLoadingCreations(true);
               // TODO: Replace with actual image generation jobs endpoint when available
               // Example endpoint: `${process.env.NEXT_PUBLIC_API_V1_URL}/image/jobs`
               const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_V1_URL}/image/jobs?limit=50`,
                    {
                         method: "GET",
                         headers: {
                              "Authorization": `Bearer ${token}`,
                              "Content-Type": "application/json",
                         },
                    }
               );

               if (response.ok) {
                    const data = await response.json();
                    setMyCreations(data.jobs || []);
                    setHasLoadedCreationsOnce(true);
               } else if (response.status === 404) {
                    // Endpoint doesn't exist yet, that's okay
                    setMyCreations([]);
                    setHasLoadedCreationsOnce(true);
               } else {
                    console.error("Failed to load creations:", response.statusText);
                    setMyCreations([]);
                    setHasLoadedCreationsOnce(true);
               }
          } catch (error) {
               console.error("Error loading creations:", error);
               setMyCreations([]);
               setHasLoadedCreationsOnce(true);
          } finally {
               setLoadingCreations(false);
          }
     };

     // Load models on mount
     useEffect(() => {
          loadModels();
     }, []);

     // Load creations when user changes or when "My Creations" tab is active
     useEffect(() => {
          if (activeTab === "creations") {
               if (user && !hasLoadedCreationsOnce) {
                    loadMyCreations();
               } else if (!user) {
                    setMyCreations([]);
                    setHasLoadedCreationsOnce(false);
               }
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [user, activeTab, hasLoadedCreationsOnce]);

     // Refresh creations when tab switches to "My Creations"
     useEffect(() => {
          if (activeTab === "creations" && user) {
               loadMyCreations();
          }
          // eslint-disable-next-line react-hooks/exhaustive-deps
     }, [activeTab]);

     // Handle drag and drop for images
     useEffect(() => {
          const dropZone = imageDropRef.current;
          if (!dropZone || mode !== "image-to-image") return;

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
                    if (file.type.startsWith("image/")) {
                         handleImageSelect(file);
                    } else {
                         setError("Please drop an image file (JPG, PNG, etc.)");
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
     }, [mode, handleImageSelect]); // Re-run when mode changes or handleImageSelect changes

     return (
          <div className="min-h-screen bg-black-1100 font-inter pt-[100px] pb-10 px-4 md:px-8 lg:px-12">
               <div className="max-w-[1200px] mx-auto">
                    {/* Header Section */}
                    <h1 className="text-2xl md:text-3xl lg:text-4xl font-medium text-white mb-8">
                         Turn Imagination Into Reality
                    </h1>

                    {/* Input Area */}
                    <div className="bg-black-1000 rounded-2xl p-6 border border-white/10 mb-12 shadow-2xl">
                         {/* Error Message */}
                         {error && (
                              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                                   <p className="text-red-400 text-sm">{error}</p>
                              </div>
                         )}
                         
                         <div className="flex items-center gap-8 mb-6 border-b border-white/5 pb-4">
                              {loadingModels || authLoading ? (
                                   <>
                                        <div className="relative w-32 h-9 bg-white/5 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                        <div className="relative w-28 h-9 bg-white/5 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   </>
                              ) : (
                                   <>
                                        <button 
                                             onClick={() => setMode("text-to-image")}
                                             className={clsx("flex items-center gap-2.5 text-sm font-medium transition-all", mode === "text-to-image" ? "text-white" : "text-white/40 hover:text-white/70")}
                                        >
                                             <div className={clsx("w-7 h-7 rounded-lg flex items-center justify-center transition-all", mode === "text-to-image" ? "bg-[#14161A] border border-[#cefb16]/30" : "bg-white/5")}>
                                                  <img src="/images/text-to-image.svg" className="w-4 h-4" alt="" />
                                             </div>
                                             Text to Image
                                        </button>
                                        <button 
                                             onClick={() => setMode("image-to-image")}
                                             className={clsx("flex items-center gap-2.5 text-sm font-medium transition-all", mode === "image-to-image" ? "text-white" : "text-white/40 hover:text-white/70")}
                                        >
                                             <div className={clsx("w-7 h-7 rounded-lg flex items-center justify-center transition-all", mode === "image-to-image" ? "bg-[#14161A] border border-[#cefb16]/30" : "bg-white/5")}>
                                                  <img src="/images/image-to-image.svg" className="w-4 h-4" alt="" />
                                             </div>
                                             Edit Image
                                        </button>
                                   </>
                              )}
                         </div>

                         <div className="flex gap-4 mb-6">
                              {mode === "image-to-image" && (
                                   <div className="flex flex-col gap-2 w-48 shrink-0">
                                        {imagePreview ? (
                                             <div className="relative h-full min-h-[100px] rounded-xl overflow-hidden border border-white/10">
                                                  <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                                                  <button
                                                       onClick={() => {
                                                            setImageFile(null);
                                                            setImagePreview(null);
                                                            setImageUrl(null);
                                                            imageUrlRef.current = null;
                                                            imageUploadTimestampRef.current = 0;
                                                       }}
                                                       className="absolute top-2 right-2 p-1.5 bg-black/60 hover:bg-black/80 rounded-lg transition-colors text-white text-xs font-bold"
                                                  >
                                                       ×
                                                  </button>
                                             </div>
                                        ) : (
                                             <label 
                                                  ref={imageDropRef}
                                                  className="h-full min-h-[100px] border border-dashed border-white/10 rounded-xl bg-black-1000 hover:bg-gray-1600 transition-colors flex flex-col items-center justify-center gap-3 group cursor-pointer"
                                             >
                                                  <input
                                                       type="file"
                                                       accept="image/*"
                                                       className="hidden"
                                                       onChange={(e) => {
                                                            const file = e.target.files?.[0];
                                                            if (file) {
                                                                 handleImageSelect(file);
                                                            }
                                                       }}
                                                  />
                                                  <div className="w-10 h-10 rounded-full bg-gray-1400 flex items-center justify-center group-hover:scale-110 transition-transform">
                                                       <img src="/images/Plus.svg" className="w-5 h-5 opacity-50" alt="" />
                                                  </div>
                                                  <span className="text-xs font-medium text-white/60">Upload Image</span>
                                             </label>
                                        )}
                                   </div>
                              )}
                              <div className="relative flex-grow">
                                   {loadingModels || authLoading ? (
                                        <div className="relative w-full h-full min-h-[100px] rounded-xl bg-white/5 overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : (
                                        <>
                                             <textarea 
                                                  value={prompt}
                                                  onChange={(e) => setPrompt(e.target.value)}
                                                  placeholder={mode === "image-to-image" ? "Describe how to transform your image (e.g. 'swap the sky with a sunset') or blend 2-3 images into one" : "Describe the image you want to generate..."}
                                                  className="w-full h-full min-h-[100px] rounded-xl border border-white/10 bg-black-1000 p-4 text-sm text-white placeholder-white/40 focus:outline-none focus:border-blue-1100 resize-none transition-colors"
                                                  style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                                             />
                                             <style jsx>{`
                                                  textarea::-webkit-scrollbar {
                                                       display: none;
                                                  }
                                             `}</style>
                                             <button className="absolute bottom-3 right-3 p-2 hover:bg-white/10 rounded-lg transition-colors text-xs text-white/40 hover:text-white flex items-center gap-1">
                                                  <div className="w-4 h-4 rounded-full border border-white/40 flex items-center justify-center text-[10px]">i</div>
                                                  Prompt tips
                                             </button>
                                        </>
                                   )}
                              </div>
                         </div>

                         <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/5 mt-4">
                              <div className="flex items-center gap-3">
                                   {/* Model Dropdown */}
                                   {loadingModels || authLoading ? (
                                        <div className="relative w-40 h-8 bg-white/5 border border-white/10 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : selectedModel && models.length > 0 ? (
                                   <Listbox value={selectedModel} onChange={setSelectedModel}>
                                        <div className="relative">
                                             <ListboxButton className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 px-2.5 text-[11px] font-medium text-white transition-colors">
                                                  {selectedModel?.icon ? (
                                                       <img src={selectedModel.icon} className="w-3.5 h-3.5" alt="" />
                                                  ) : (
                                                       <img src="/images/MagicWand.svg" className="w-3.5 h-3.5" alt="" />
                                                  )}
                                                       {selectedModel?.display_name || selectedModel?.name || "Select Model"}
                                                  <img src="/images/droparrow.svg" className="w-2.5 h-2.5 opacity-50 ml-auto" alt="" />
                                             </ListboxButton>
                                             <ListboxOptions className="absolute top-full left-0 mt-2 w-40 bg-[#25282F] border border-white/10 rounded-xl p-1 focus:outline-none z-50">
                                                  {models.map((model) => (
                                                       <ListboxOption
                                                            key={model.id}
                                                            value={model}
                                                            className="group flex cursor-default items-center gap-2 rounded-lg py-1.5 px-2.5 select-none data-[focus]:bg-white/10"
                                                       >
                                                            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/5">
                                                                 {model.icon ? (
                                                                      <img src={model.icon} alt="" className="w-4 h-4" />
                                                                 ) : (
                                                                      <img src="/images/MagicWand.svg" alt="" className="w-4 h-4" />
                                                                 )}
                                                            </div>
                                                            <span className="text-xs font-medium text-white">{model.display_name || model.name}</span>
                                                       </ListboxOption>
                                                  ))}
                                             </ListboxOptions>
                                        </div>
                                   </Listbox>
                                   ) : (
                                        <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg py-1.5 px-2.5 text-[11px] font-medium text-white/40">
                                             <img src="/images/MagicWand.svg" className="w-3.5 h-3.5" alt="" />
                                             No models available
                                        </div>
                                   )}

                                   {/* Aspect Ratio Dropdown */}
                                   {loadingModels || authLoading ? (
                                        <div className="relative w-20 h-8 bg-white/5 border border-white/10 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : selectedModel?.supports_aspect_ratio && (
                                   <Listbox value={selectedRatio} onChange={setSelectedRatio}>
                                        <div className="relative">
                                             <ListboxButton className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 px-2.5 text-[11px] font-medium text-white transition-colors">
                                                  <img src="/images/image-ratio.svg" className="w-3.5 h-3.5" alt="" />
                                                       {selectedRatio}
                                                  <img src="/images/droparrow.svg" className="w-2.5 h-2.5 opacity-50 ml-auto" alt="" />
                                             </ListboxButton>
                                             <ListboxOptions className="absolute bottom-full left-0 mb-2 w-24 bg-[#25282F] border border-white/10 rounded-xl p-1 focus:outline-none z-50">
                                                       {getAvailableAspectRatios().map((ratio: any) => (
                                                       <ListboxOption
                                                            key={ratio.id}
                                                                 value={ratio.name}
                                                            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] text-white rounded-lg cursor-pointer hover:bg-white/10 data-[selected]:bg-white/10"
                                                       >
                                                            {ratio.name}
                                                       </ListboxOption>
                                                  ))}
                                             </ListboxOptions>
                                        </div>
                                   </Listbox>
                                   )}

                                   {/* Resolution Dropdown */}
                                   {loadingModels || authLoading ? (
                                        <div className="relative w-20 h-8 bg-white/5 border border-white/10 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : selectedModel?.supports_resolution && (
                                        <Listbox value={selectedResolution} onChange={setSelectedResolution}>
                                             <div className="relative">
                                                  <ListboxButton className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 px-2.5 text-[11px] font-medium text-white transition-colors">
                                                       <span className="text-[11px]">Res</span>
                                                       {selectedResolution}
                                                       <img src="/images/droparrow.svg" className="w-2.5 h-2.5 opacity-50 ml-auto" alt="" />
                                                  </ListboxButton>
                                                  <ListboxOptions className="absolute bottom-full left-0 mb-2 w-20 bg-[#25282F] border border-white/10 rounded-xl p-1 focus:outline-none z-50">
                                                       {getAvailableResolutions().map((res: any) => (
                                                            <ListboxOption
                                                                 key={res.id}
                                                                 value={res.name}
                                                                 className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] text-white rounded-lg cursor-pointer hover:bg-white/10 data-[selected]:bg-white/10"
                                                            >
                                                                 {res.name}
                                                            </ListboxOption>
                                                       ))}
                                                  </ListboxOptions>
                                             </div>
                                        </Listbox>
                                   )}

                                   {/* Output Format Dropdown */}
                                   {loadingModels || authLoading ? (
                                        <div className="relative w-20 h-8 bg-white/5 border border-white/10 rounded-lg overflow-hidden">
                                             <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                        </div>
                                   ) : selectedModel?.supports_output_format && (
                                        <Listbox value={selectedOutputFormat} onChange={setSelectedOutputFormat}>
                                             <div className="relative">
                                                  <ListboxButton className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg py-1.5 px-2.5 text-[11px] font-medium text-white transition-colors">
                                                       <span className="text-[11px]">Format</span>
                                                       {selectedOutputFormat.toUpperCase()}
                                                       <img src="/images/droparrow.svg" className="w-2.5 h-2.5 opacity-50 ml-auto" alt="" />
                                                  </ListboxButton>
                                                  <ListboxOptions className="absolute bottom-full left-0 mb-2 w-20 bg-[#25282F] border border-white/10 rounded-xl p-1 focus:outline-none z-50">
                                                       {getAvailableOutputFormats().map((format: any) => (
                                                            <ListboxOption
                                                                 key={format.id}
                                                                 value={format.id}
                                                                 className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] text-white rounded-lg cursor-pointer hover:bg-white/10 data-[selected]:bg-white/10"
                                                            >
                                                                 {format.name}
                                                            </ListboxOption>
                                                       ))}
                                                  </ListboxOptions>
                                             </div>
                                        </Listbox>
                                   )}
                              </div>

                              {loadingModels || authLoading ? (
                                   <div className="relative w-32 h-11 bg-white/5 rounded-xl overflow-hidden">
                                        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
                                   </div>
                              ) : (
                              <button 
                                   onClick={async () => {
                                        if (!user) {
                                             router.push("/signup");
                                             return;
                                        }
                                        
                                        // Clear previous errors
                                        setError(null);
                                        
                                        if (!prompt.trim()) {
                                             setError("Please enter a prompt to generate an image");
                                             return;
                                        }
                                        
                                        if (!selectedModel) {
                                             setError("Please select a model");
                                             return;
                                        }

                                        // For image-to-image mode, require image upload
                                        if (mode === "image-to-image" && !imageFile && !imageUrl) {
                                             setError("Please upload an image to edit");
                                             return;
                                        }
                                        
                                        if (isGenerating || imageUploading) return;
                                        
                                        // Switch to "My Creations" tab immediately
                                        setActiveTab("creations");
                                        
                                        try {
                                             setError(null);
                                             
                                             const token = getToken();
                                             if (!token) {
                                                  router.push("/login");
                                                  return;
                                             }

                                             // Clear image from frontend immediately when generation starts
                                             // This allows user to upload new image right away
                                             const currentImageFile = imageFile;
                                             const currentImageUrl = imageUrlRef.current || imageUrl;
                                             if (mode === "image-to-image") {
                                                  setImageFile(null);
                                                  setImagePreview(null);
                                                  setImageUrl(null);
                                                  imageUrlRef.current = null;
                                                  imageUploadTimestampRef.current = 0;
                                                  // Clear the file input field
                                                  const imageInput = document.querySelector('input[type="file"][accept*="image"]') as HTMLInputElement;
                                                  if (imageInput) {
                                                       imageInput.value = '';
                                                  }
                                             }

                                             // Upload image to Backblaze if we have a file but no URL yet
                                             let finalImageUrl = currentImageUrl;
                                             
                                             if (mode === "image-to-image" && currentImageFile && !finalImageUrl) {
                                                  console.log("📤 Uploading image to Backblaze before generation...");
                                                  setImageUploading(true);
                                                  
                                                  try {
                                                       const uploadStartTime = Date.now();
                                                       const url = await uploadFileToBackblaze(currentImageFile);
                                                       
                                                       if (url) {
                                                            // Set ref FIRST (synchronous, immediate)
                                                            imageUrlRef.current = url;
                                                            imageUploadTimestampRef.current = uploadStartTime;
                                                            
                                                            // Then set state
                                                            setImageUrl(url);
                                                            
                                                            finalImageUrl = url;
                                                            console.log("✅ Image uploaded to Backblaze:", url);
                                                       } else {
                                                            throw new Error("Failed to upload image to Backblaze");
                                                       }
                                                  } catch (uploadError: any) {
                                                       console.error("❌ Image upload failed:", uploadError);
                                                       setImageUploading(false);
                                                       throw new Error(`Failed to upload image: ${uploadError.message || "Unknown error"}`);
                                                  } finally {
                                                       setImageUploading(false);
                                                  }
                                             }
                                             
                                             setIsGenerating(true);
                                             setOutputUrl(null);
                                             
                                             const requestBody: any = {
                                                  prompt: prompt,
                                                  model: selectedModel.id,
                                             };
                                             
                                             // Add image_url for image-to-image mode
                                             if (mode === "image-to-image" && finalImageUrl) {
                                                  requestBody.image_url = finalImageUrl;
                                             }
                                             
                                             if (selectedModel.supports_aspect_ratio && selectedRatio) {
                                                  requestBody.aspect_ratio = selectedRatio;
                                             }
                                             if (selectedModel.supports_resolution && selectedResolution) {
                                                  requestBody.resolution = selectedResolution;
                                             }
                                             if (selectedModel.supports_output_format && selectedOutputFormat) {
                                                  requestBody.output_format = selectedOutputFormat;
                                             }
                                             
                                             const response = await fetch(`${process.env.NEXT_PUBLIC_API_V1_URL}/image/submit`, {
                                                  method: "POST",
                                                  headers: {
                                                       "Authorization": `Bearer ${token}`,
                                                       "Content-Type": "application/json",
                                                  },
                                                  body: JSON.stringify(requestBody),
                                             });
                                             
                                             const data = await response.json();
                                             
                                             if (!response.ok) {
                                                  throw new Error(data.detail || "Failed to submit job");
                                             }
                                             
                                             setJobId(data.job_id);
                                             
                                             // Poll for job status
                                             const pollJobStatus = async () => {
                                                  try {
                                                       const statusResponse = await fetch(
                                                            `${process.env.NEXT_PUBLIC_API_V1_URL}/image/jobs/${data.job_id}`,
                                                            {
                                                                 headers: {
                                                                      "Authorization": `Bearer ${token}`,
                                                                 },
                                                            }
                                                       );
                                                       
                                                       if (statusResponse.ok) {
                                                            const statusData = await statusResponse.json();
                                                            if (statusData.output_url) {
                                                                 setOutputUrl(statusData.output_url);
                                                                 setIsGenerating(false);
                                                                 loadMyCreations();
                                                                 return;
                                                            }
                                                            if (statusData.status === "failed") {
                                                                 setIsGenerating(false);
                                                                 setError(`Generation failed: ${statusData.error || "Unknown error"}`);
                                                                 return;
                                                            }
                                                       }
                                                       
                                                       // Continue polling if not completed
                                                       setTimeout(pollJobStatus, 3000);
                                                  } catch (error) {
                                                       console.error("Error polling job status:", error);
                                                       setTimeout(pollJobStatus, 3000);
                                                  }
                                             };
                                             
                                             // Start polling after 3 seconds
                                             setTimeout(pollJobStatus, 3000);
                                        } catch (error: any) {
                                             console.error("Error generating image:", error);
                                             setIsGenerating(false);
                                             setError(error.message || "Failed to generate image. Please try again.");
                                        }
                                   }}
                                   disabled={!!user && (isGenerating || imageUploading || !prompt.trim() || !selectedModel || (mode === "image-to-image" && !imageFile && !imageUrl))}
                                   className={clsx(
                                        "flex items-center gap-2 text-sm font-bold py-2.5 px-5 rounded-xl transition-all duration-300 shadow-3xl hover:shadow-7xl hover:-translate-y-0.5 bg1 text-black",
                                        // Only show disabled styling for logged in users when fields are missing
                                        user && (isGenerating || imageUploading || !prompt.trim() || !selectedModel || (mode === "image-to-image" && !imageFile && !imageUrl)) 
                                             ? "cursor-not-allowed" 
                                             : ""
                                   )}
                              >
                                   {(() => {
                                        if (imageUploading) return "Uploading...";
                                        if (isGenerating) return "Generating...";
                                        if (!user) return "Generate";
                                        if (!selectedModel) return "Generate";
                                        const modelId = selectedModel.id;
                                        const credits = getRequiredCreditsSync(modelId, selectedResolution);
                                        if (credits > 0) {
                                             return `Generate (${credits})`;
                                        }
                                        return "Generate";
                                   })()}
                                   <img src="/images/MagicWand.svg" className="w-4 h-4 brightness-0" alt="" />
                              </button>
                              )}
                         </div>
                    </div>

                    {/* Gallery Tabs */}
                    <div className="flex items-center gap-6 mb-6 border-b border-white/10">
                         <button 
                              onClick={() => setActiveTab("explore")}
                              className={clsx(
                                   "pb-3 text-sm font-medium transition-all relative", 
                                   activeTab === "explore" ? "text-white" : "text-white/40 hover:text-white/70"
                              )}
                         >
                              Explore
                              {activeTab === "explore" && (
                                   <span className="absolute bottom-0 left-0 w-full h-[1px] bg-[#F4D06F]" />
                              )}
                         </button>
                         <button 
                              onClick={() => setActiveTab("creations")}
                              className={clsx(
                                   "pb-3 text-sm font-medium transition-all relative", 
                                   activeTab === "creations" ? "text-white" : "text-white/40 hover:text-white/70"
                              )}
                         >
                              My Creations
                              {activeTab === "creations" && (
                                   <span className="absolute bottom-0 left-0 w-full h-[1px] bg-[#F4D06F]" />
                              )}
                         </button>
                    </div>

                    {/* Masonry Grid */}
                    {activeTab === "explore" ? (
                    <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
                         {galleryImages.map((img, idx) => (
                              <div key={`${img.id}-${idx}`} className={`break-inside-avoid relative group rounded-xl overflow-hidden bg-[#1A1D24] ${img.aspect}`}>
                                   <img 
                                        src={img.src} 
                                        alt="" 
                                        className="w-full h-full object-cover"
                                        loading={idx < 4 ? "eager" : "lazy"}
                                        decoding="async"
                                   />
                                   <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-3">
                                        <div className="flex items-center gap-2">
                                             <span className="text-[10px] font-medium text-white bg-white/20 backdrop-blur-sm px-2 py-0.5 rounded">IMAGE</span>
                                        </div>
                                   </div>
                              </div>
                         ))}
                    </div>
                    ) : (
                         <>
                              {loadingCreations || (user && !hasLoadedCreationsOnce) ? (
                                   <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
                                        {[...Array(8)].map((_, idx) => (
                                             <div key={idx} className="break-inside-avoid relative rounded-xl overflow-hidden bg-gray-1600/20 animate-pulse">
                                                  <div className="w-full aspect-square bg-gray-1400/30"></div>
                                             </div>
                                        ))}
                                   </div>
                              ) : !user ? (
                                   <div className="flex flex-col items-center justify-center py-20 text-center">
                                        <p className="text-white/60 text-sm mb-4">Please sign in to view your creations</p>
                                        <button
                                             onClick={() => router.push("/signup")}
                                             className="md:text-sm text-xs text-center font-bold leading-[120%] text-black inline-flex items-center justify-center gap-2 py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300"
                                        >
                                             Get Started
                                        </button>
                                   </div>
                              ) : myCreations.length === 0 ? (
                                   <div className="flex flex-col items-center justify-center py-20 text-center">
                                        <p className="text-white/60 text-sm">You haven't created any images yet</p>
                                        <p className="text-white/40 text-xs mt-2">Start generating to see your creations here</p>
                                   </div>
                              ) : (
                                   <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
                                        {myCreations
                                             .filter((job: any) => job.output_url || job.status === "pending" || job.status === "running")
                                             .map((job: any, idx: number) => {
                                                  const hasOutput = !!job.output_url;
                                                  
                                                  // Download function - preserves original format (PNG/JPEG) instead of WebP
                                                  const forceDownload = async (url: string, filename: string, outputFormat?: string) => {
                                                       try {
                                                            const response = await fetch(url);
                                                            let blob = await response.blob();
                                                            
                                                            // Determine the correct file extension from output_format or blob type
                                                            let fileExtension = outputFormat || 'jpg';
                                                            const blobType = blob.type;
                                                            
                                                            // Normalize format names
                                                            if (fileExtension === 'jpeg') fileExtension = 'jpg';
                                                            
                                                            // Check if we need to convert the blob
                                                            const needsConversion = 
                                                                 (outputFormat && blobType !== `image/${outputFormat}` && blobType !== `image/jpeg` && outputFormat === 'jpg') ||
                                                                 (outputFormat && blobType !== `image/${outputFormat}` && outputFormat === 'png') ||
                                                                 (!outputFormat && blobType === 'image/webp');
                                                            
                                                            if (needsConversion) {
                                                                 // Convert blob to the desired format using canvas
                                                                 const img = new Image();
                                                                 const canvas = document.createElement('canvas');
                                                                 const ctx = canvas.getContext('2d');
                                                                 
                                                                 if (!ctx) {
                                                                      throw new Error('Canvas context not available');
                                                                 }
                                                                 
                                                                 await new Promise<void>((resolve, reject) => {
                                                                      img.onload = () => {
                                                                           canvas.width = img.width;
                                                                           canvas.height = img.height;
                                                                           ctx.drawImage(img, 0, 0);
                                                                           
                                                                           // Determine MIME type for conversion
                                                                           const mimeType = outputFormat === 'png' ? 'image/png' : 'image/jpeg';
                                                                           
                                                                           canvas.toBlob((convertedBlob) => {
                                                                                if (convertedBlob) {
                                                                                     blob = convertedBlob;
                                                                                     resolve();
                                                                                } else {
                                                                                     reject(new Error('Failed to convert blob'));
                                                                                }
                                                                           }, mimeType, 0.95);
                                                                      };
                                                                      img.onerror = () => reject(new Error('Failed to load image'));
                                                                      img.src = URL.createObjectURL(blob);
                                                                 });
                                                                 
                                                                 // Clean up the temporary object URL
                                                                 URL.revokeObjectURL(img.src);
                                                            } else if (!outputFormat) {
                                                                 // Try to determine format from blob type if no output_format specified
                                                                 if (blobType === 'image/png') {
                                                                      fileExtension = 'png';
                                                                 } else if (blobType === 'image/jpeg' || blobType === 'image/jpg') {
                                                                      fileExtension = 'jpg';
                                                                 }
                                                            }
                                                            
                                                            // Update filename with correct extension
                                                            const baseFilename = filename.split('.')[0];
                                                            const finalFilename = `${baseFilename}.${fileExtension}`;
                                                            
                                                            const blobUrl = window.URL.createObjectURL(blob);
                                                            const link = document.createElement('a');
                                                            link.href = blobUrl;
                                                            link.download = finalFilename;
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
                                                       <div key={job.job_id || idx} className="break-inside-avoid relative group rounded-xl overflow-hidden bg-[#1A1D24] cursor-pointer" onClick={() => hasOutput && setSelectedImageOverlay(job.output_url)}>
                                                            {hasOutput ? (
                                                                 <img src={job.output_url} alt={job.prompt || "Generated image"} className="w-full h-auto object-cover" />
                                                            ) : (
                                                                 <div className="w-full aspect-square bg-gray-1400/30 flex items-center justify-center">
                                                                      <div className="text-white/40 text-xs">Generating...</div>
                                                                 </div>
                                                            )}
                                                            
                                                            {/* AI Model Label (Bottom Left - shown on hover) */}
                                                            {(job.model_display_name || job.settings?.model_display_name) && (
                                                                 <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-md border border-white/10 text-white text-[9px] font-medium px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                                                                      {job.model_display_name || job.settings?.model_display_name}
                                                                 </div>
                                                            )}

                                                            {/* Download Button (Top Right - Always Visible) */}
                                                            {hasOutput && (
                                                                 <button
                                                                      onClick={(e) => {
                                                                           e.stopPropagation();
                                                                           // Get output format from job settings, fallback to 'jpg'
                                                                           const outputFormat = job.settings?.output_format || job.output_format || 'jpg';
                                                                           forceDownload(job.output_url, `image-${job.job_id?.slice(0, 8) || idx}`, outputFormat);
                                                                      }}
                                                                      className="absolute top-2 right-2 bg-black/40 backdrop-blur-md border border-white/10 text-white p-1.5 rounded-lg hover:bg-black/60 hover:border-white/20 transition-all z-20 shadow-lg"
                                                                      title="Download Image"
                                                                 >
                                                                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                                           <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                                                           <polyline points="7 10 12 15 17 10"></polyline>
                                                                           <line x1="12" y1="15" x2="12" y2="3"></line>
                                                                      </svg>
                                                                 </button>
                                                            )}
                                                            
                                                            {/* Status Badge (Bottom Right - shown on hover) */}
                                                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-end p-3 pointer-events-none">
                                                                 <div className="flex items-center gap-2">
                                                                      <span className="text-[10px] font-medium text-white bg-white/20 backdrop-blur-sm px-2 py-0.5 rounded">
                                                                           {job.status === "completed" ? "IMAGE" : job.status?.toUpperCase() || "PENDING"}
                                                                      </span>
                                                                 </div>
                                                            </div>
                                                       </div>
                                                  );
                                             })}
                                   </div>
                              )}
                         </>
                    )}
               </div>
               
               {/* Generating indicator - shows when job is in progress */}
               {isGenerating && !outputUrl && (
                    <div className="fixed bottom-8 right-8 z-50 bg-black-1000 border border-gray-1100 p-4 rounded-xl shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom-4">
                         <div className="w-12 h-12 rounded-lg overflow-hidden relative">
                              <div className="w-full h-full bg-gray-1100 flex items-center justify-center">
                                   <div className="w-6 h-6 border-2 border-blue-1100 border-t-transparent rounded-full animate-spin"></div>
                              </div>
                         </div>
                         <div>
                              <h4 className="text-sm font-medium text-white">Generating Image...</h4>
                              <p className="text-xs text-white/60">This may take a few moments</p>
                         </div>
                    </div>
               )}

               {/* Image Overlay Modal */}
               {selectedImageOverlay && (
                    <div 
                         className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
                         onClick={() => setSelectedImageOverlay(null)}
                    >
                         {/* Blurred Background */}
                         <div className="absolute inset-0 bg-black/80 backdrop-blur-md"></div>
                         
                         {/* Close Button */}
                         <button
                              onClick={() => setSelectedImageOverlay(null)}
                              className="absolute top-4 right-4 z-10 bg-black/60 hover:bg-black/80 backdrop-blur-md border border-white/20 text-white p-3 rounded-full transition-all hover:scale-110"
                              aria-label="Close"
                         >
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                   <line x1="18" y1="6" x2="6" y2="18"></line>
                                   <line x1="6" y1="6" x2="18" y2="18"></line>
                              </svg>
                         </button>

                         {/* Large Image */}
                         <div 
                              className="relative z-10 max-w-[90vw] max-h-[90vh] w-auto h-auto"
                              onClick={(e) => e.stopPropagation()}
                         >
                              <img 
                                   src={selectedImageOverlay} 
                                   alt="Full size preview" 
                                   className="max-w-full max-h-[90vh] w-auto h-auto object-contain rounded-lg shadow-2xl"
                              />
                         </div>
                    </div>
               )}
          </div>
     );
}

