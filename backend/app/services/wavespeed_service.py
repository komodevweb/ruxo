"""
WaveSpeed AI Service for Wan 2.2 Animate integration.
Handles API communication with WaveSpeed AI and job status polling.
"""
import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class WaveSpeedService:
    """Service for interacting with WaveSpeed AI API."""
    
    def __init__(self):
        """Initialize WaveSpeed AI service."""
        if not settings.WAVESPEED_API_KEY:
            logger.warning("WAVESPEED_API_KEY not configured. WaveSpeed AI features will be disabled.")
            self.api_key = None
        else:
            self.api_key = settings.WAVESPEED_API_KEY
            logger.debug("WaveSpeed AI service initialized")
        
        self.base_url = settings.WAVESPEED_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
    
    async def submit_wan_animate_job(
        self,
        image_url: str,
        video_url: str,
        mode: str = "animate",
        resolution: str = "480p",
        prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Wan 2.2 Animate job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (must be accessible by WaveSpeed)
            video_url: URL to the input video (must be accessible by WaveSpeed)
            mode: "animate" or "replace" (default: "animate")
            resolution: "480p" or "720p" (default: "480p")
            prompt: Optional prompt for generation rules
            seed: Random seed (-1 for random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Wan 2.2 Animate job: mode={mode}, resolution={resolution}, seed={seed}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Video URL: {video_url}")
        if prompt:
            logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/wavespeed-ai/wan-2.2/animate"
        
        payload = {
            "image": image_url,
            "video": video_url,
            "mode": mode,
            "resolution": resolution,
            "seed": seed
        }
        
        if prompt:
            payload["prompt"] = prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_text_to_video(
        self,
        model_endpoint: str,
        prompt: str,
        size: str = "1280*720",
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        audio_url: Optional[str] = None,
        enable_prompt_expansion: bool = False,
        seed: int = -1,
        aspect_ratio: Optional[str] = None,
        camera_fixed: Optional[bool] = None,
        generate_audio: Optional[bool] = None,
        resolution: Optional[str] = None,
        guidance_scale: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Submit a Text To Video job to WaveSpeed AI.
        Generic method that works with any model endpoint.
        
        Args:
            model_endpoint: The API endpoint for the specific model (e.g., "/alibaba/wan-2.5/text-to-video")
            prompt: The positive prompt for generation (required)
            size: Video size in pixels (width*height)
            duration: Video duration in seconds
            negative_prompt: Optional negative prompt
            audio_url: Optional audio URL to guide generation
            enable_prompt_expansion: Enable prompt optimizer
            seed: Random seed (-1 for random)
            **kwargs: Additional model-specific parameters
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Text To Video job: endpoint={model_endpoint}, size={size}, duration={duration}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        if audio_url:
            logger.info(f"Audio URL: {audio_url}")
        
        url = f"{self.base_url}{model_endpoint}"
        
        payload = {
            "prompt": prompt
        }
        
        # Only add parameters if they are provided (some models don't support all parameters)
        if duration is not None:
            payload["duration"] = duration
        if seed is not None and seed != -1:
            payload["seed"] = seed
        
        # Some models use aspect_ratio instead of size
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        elif size:
            payload["size"] = size
        
        # Some models use resolution parameter (e.g., Veo 3, Veo 3.1)
        if resolution:
            payload["resolution"] = resolution
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if audio_url:
            payload["audio"] = audio_url
        if enable_prompt_expansion is not None:
            payload["enable_prompt_expansion"] = enable_prompt_expansion
        if camera_fixed is not None:
            payload["camera_fixed"] = camera_fixed
        if generate_audio is not None:
            payload["generate_audio"] = generate_audio
        if guidance_scale is not None:
            payload["guidance_scale"] = guidance_scale
        
        # Add any additional model-specific parameters
        payload.update(kwargs)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_wan_2_5_image_to_video(
        self,
        image_url: str,
        prompt: str,
        resolution: str = "720p",
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        audio_url: Optional[str] = None,
        enable_prompt_expansion: bool = False,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Wan 2.5 Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required)
            resolution: Video resolution. Options: "480p", "720p", "1080p" (default: "720p")
            duration: Video duration in seconds (3-10, default: 5)
            negative_prompt: Optional negative prompt
            audio_url: Optional audio URL to guide generation (WAV/MP3, 3-30s, ≤15MB)
            enable_prompt_expansion: Enable prompt optimizer
            seed: Random seed (-1 for random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Wan 2.5 Image To Video job: resolution={resolution}, duration={duration}, seed={seed}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        if audio_url:
            logger.info(f"Audio URL: {audio_url}")
        
        url = f"{self.base_url}/alibaba/wan-2.5/image-to-video"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "resolution": resolution,
            "duration": duration,
            "enable_prompt_expansion": enable_prompt_expansion,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        if audio_url:
            payload["audio"] = audio_url  # API expects "audio" parameter, not "audio_url"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_google_veo_3_fast_image_to_video(
        self,
        image_url: str,
        prompt: str,
        aspect_ratio: str = "16:9",
        duration: int = 8,
        resolution: str = "720p",
        generate_audio: bool = True,
        negative_prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Google Veo 3 Fast Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required)
            aspect_ratio: Aspect ratio. Options: "16:9", "9:16" (default: "16:9")
            duration: Video duration in seconds (4, 6, 8, default: 8)
            resolution: Video resolution. Options: "720p", "1080p" (default: "720p")
            generate_audio: Whether to generate audio (default: True)
            negative_prompt: Optional negative prompt
            seed: Random seed (-1 for random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Veo 3 Fast Image To Video job: aspect_ratio={aspect_ratio}, duration={duration}, resolution={resolution}, generate_audio={generate_audio}, seed={seed}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        
        url = f"{self.base_url}/google/veo3-fast/image-to-video"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "resolution": resolution,
            "generate_audio": generate_audio,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_google_veo_3_1_fast_image_to_video(
        self,
        image_url: str,
        prompt: str,
        aspect_ratio: str = "16:9",
        duration: int = 8,
        resolution: str = "720p",
        generate_audio: bool = True,
        negative_prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Google Veo 3.1 Fast Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required)
            aspect_ratio: Aspect ratio. Options: "16:9", "9:16" (default: "16:9")
            duration: Video duration in seconds (4, 6, 8, default: 8)
            resolution: Video resolution. Options: "720p", "1080p" (default: "720p")
            generate_audio: Whether to generate audio (default: True)
            negative_prompt: Optional negative prompt
            seed: Random seed (-1 for random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Veo 3.1 Fast Image To Video job: aspect_ratio={aspect_ratio}, duration={duration}, resolution={resolution}, generate_audio={generate_audio}, seed={seed}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        
        url = f"{self.base_url}/google/veo3.1/image-to-video"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "resolution": resolution,
            "generate_audio": generate_audio,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_openai_sora_2_image_to_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 4
    ) -> Dict[str, Any]:
        """
        Submit an OpenAI Sora 2 Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required)
            duration: Video duration in seconds (4, 8, 12, default: 4)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting OpenAI Sora 2 Image To Video job: duration={duration}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/openai/sora-2/image-to-video"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "duration": duration
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_openai_sora_2_pro_image_to_video(
        self,
        image_url: str,
        prompt: str,
        resolution: str = "720p",
        duration: int = 4
    ) -> Dict[str, Any]:
        """
        Submit an OpenAI Sora 2 Pro Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required)
            resolution: Video resolution. Options: "720p", "1080p" (default: "720p")
                       Will be converted to size format: 720p -> "1280*720", 1080p -> "1792*1024"
            duration: Video duration in seconds (4, 8, 12, default: 4)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        # Convert resolution to size format (matching text-to-video API)
        # 720p can be landscape (1280*720) or portrait (720*1280)
        # 1080p can be landscape (1792*1024) or portrait (1024*1792)
        # Default to landscape for simplicity
        size_mapping = {
            "720p": "1280*720",
            "1080p": "1792*1024"
        }
        size = size_mapping.get(resolution, "1280*720")
        
        logger.info(f"Submitting OpenAI Sora 2 Pro Image To Video job: resolution={resolution} -> size={size}, duration={duration}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/openai/sora-2/image-to-video-pro"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "size": size,
            "duration": duration
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_kling_v2_5_turbo_pro_image_to_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        guidance_scale: Optional[float] = None,
        last_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a Kling V2.5 Turbo Pro Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: The positive prompt for generation (required, max 2500 chars)
            duration: Video duration in seconds (5 or 10, default: 5)
            negative_prompt: Optional negative prompt (max 2500 chars)
            guidance_scale: Guidance scale (0.0-1.0, default: 0.5)
            last_image_url: Optional end frame image URL for first-last frame animation
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Kling V2.5 Turbo Pro Image To Video job: duration={duration}, guidance_scale={guidance_scale}")
        logger.info(f"Image URL: {image_url}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        if last_image_url:
            logger.info(f"Last image URL: {last_image_url}")
        
        url = f"{self.base_url}/kwaivgi/kling-v2.5-turbo-pro/image-to-video"
        
        payload = {
            "image": image_url,
            "prompt": prompt,
            "duration": duration
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if guidance_scale is not None:
            payload["guidance_scale"] = guidance_scale
        if last_image_url:
            payload["last_image"] = last_image_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_hailuo_2_3_i2v_standard_image_to_video(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        duration: int = 6,
        enable_prompt_expansion: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Minimax Hailuo 2.3 I2V Standard Image To Video job to WaveSpeed AI.
        
        Args:
            image_url: URL to the input image (required)
            prompt: Optional text prompt for generation
            duration: Video duration in seconds (6 or 10, default: 6)
            enable_prompt_expansion: Enable automatic prompt optimization (default: False)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Hailuo 2.3 I2V Standard Image To Video job: duration={duration}, enable_prompt_expansion={enable_prompt_expansion}")
        logger.info(f"Image URL: {image_url}")
        if prompt:
            logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/minimax/hailuo-2.3/i2v-standard"
        
        payload = {
            "image": image_url,
            "duration": duration,
            "enable_prompt_expansion": enable_prompt_expansion
        }
        
        if prompt:
            payload["prompt"] = prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_hailuo_2_3_i2v_pro_image_to_video(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        enable_prompt_expansion: bool = True
    ) -> Dict[str, Any]:
        """
        Submit a Minimax Hailuo 2.3 I2V Pro Image To Video job to WaveSpeed AI.
        
        According to API docs: https://wavespeed.ai/docs/docs-api/minimax/minimax-hailuo-2.3-i2v-pro
        
        Args:
            image_url: URL to the input image (required) - Base64 or public URL
            prompt: Optional text prompt for generation (optional)
            enable_prompt_expansion: Enable automatic prompt optimization (default: True)
        
        Returns:
            Dictionary with job information including task ID and status
        
        Note:
            - Fixed duration: 5 seconds
            - Fixed resolution: 1080p
            - Cost: $0.49 per job
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Hailuo 2.3 I2V Pro Image To Video job: enable_prompt_expansion={enable_prompt_expansion}")
        logger.info(f"Image URL: {image_url}")
        if prompt:
            logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/minimax/hailuo-2.3/i2v-pro"
        
        payload = {
            "image": image_url,
            "enable_prompt_expansion": enable_prompt_expansion
        }
        
        if prompt:
            payload["prompt"] = prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {error_text}")
            
            # Try to extract detailed error message from API response
            api_error_message = None
            try:
                error_json = e.response.json()
                api_error_message = error_json.get("message") or error_json.get("detail") or error_json.get("error")
                if api_error_message:
                    logger.error(f"WaveSpeed API error details: {api_error_message}")
            except:
                pass
            
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Include detailed error message from API if available
                if api_error_message:
                    raise Exception(f"WaveSpeed API error: {api_error_message}")
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_wan_2_5_text_to_video(
        self,
        prompt: str,
        size: str = "1280*720",
        duration: int = 5,
        negative_prompt: Optional[str] = None,
        audio_url: Optional[str] = None,
        enable_prompt_expansion: bool = False,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Wan 2.5 Text To Video job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            size: Video size in pixels (width*height). Options: 832*480, 480*832, 1280*720, 720*1280, 1920*1080, 1080*1920
            duration: Video duration in seconds (5 or 10)
            negative_prompt: Optional negative prompt
            audio_url: Optional audio URL to guide generation (WAV/MP3, 3-30s, ≤15MB)
            enable_prompt_expansion: Enable prompt optimizer
            seed: Random seed (-1 for random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Wan 2.5 Text To Video job: size={size}, duration={duration}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        if audio_url:
            logger.info(f"Audio URL: {audio_url}")
        
        """Legacy method for Wan 2.5 - uses the generic submit_text_to_video method."""
        return await self.submit_text_to_video(
            model_endpoint="/alibaba/wan-2.5/text-to-video",
            prompt=prompt,
            size=size,
            duration=duration,
            negative_prompt=negative_prompt,
            audio_url=audio_url,
            enable_prompt_expansion=enable_prompt_expansion,
            seed=seed
        )
    
    async def get_job_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get the result of a WaveSpeed AI job.
        
        Args:
            task_id: The task ID returned from submit_wan_animate_job or submit_wan_2_5_text_to_video
        
        Returns:
            Dictionary with job status and results
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        url = f"{self.base_url}/predictions/{task_id}/result"
        
        logger.info(f"Checking job status for task_id: {task_id}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"GET {url}")
                response = await client.get(
                    url,
                    headers=self.headers
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                status = result.get('data', {}).get('status', 'unknown')
                logger.info(f"Job status for {task_id}: {status}")
                
                if status == "completed":
                    outputs = result.get('data', {}).get('outputs', [])
                    logger.info(f"Job completed with {len(outputs)} output(s)")
                    for i, output in enumerate(outputs):
                        logger.info(f"Output {i+1}: {output}")
                elif status == "failed":
                    error = result.get('data', {}).get('error', 'Unknown error')
                    logger.error(f"Job failed: {error}")
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting WaveSpeed job result: {e}", exc_info=True)
            raise
    
    async def submit_google_nano_banana_pro_text_to_image(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        resolution: str = "1k",
        output_format: str = "jpeg",
        enable_sync_mode: bool = False,
        enable_base64_output: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Google Nano Banana Pro Text-to-Image job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            aspect_ratio: Aspect ratio (1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
            resolution: Resolution (1k, 2k, 4k) - default: "1k"
            output_format: Output format (jpeg, png) - default: "jpeg"
            enable_sync_mode: If true, wait for result before returning
            enable_base64_output: If true, return base64 encoded output
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Nano Banana Pro Text-to-Image job: resolution={resolution}, aspect_ratio={aspect_ratio}, output_format={output_format}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/google/nano-banana-pro/text-to-image"
        
        payload = {
            "prompt": prompt,
            "resolution": resolution,
            "output_format": output_format,
            "enable_sync_mode": enable_sync_mode,
            "enable_base64_output": enable_base64_output
        }
        
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting WaveSpeed job: {e}", exc_info=True)
            raise
    
    async def submit_google_nano_banana_text_to_image(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        output_format: str = "jpeg",
        enable_sync_mode: bool = False,
        enable_base64_output: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Google Nano Banana Text-to-Image job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            aspect_ratio: Aspect ratio (1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
            output_format: Output format (jpeg, png) - default: "jpeg"
            enable_sync_mode: If true, wait for result before returning
            enable_base64_output: If true, return base64 encoded output
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Nano Banana Text-to-Image job: aspect_ratio={aspect_ratio}, output_format={output_format}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/google/nano-banana/text-to-image"
        
        payload = {
            "prompt": prompt,
            "output_format": output_format,
            "enable_sync_mode": enable_sync_mode,
            "enable_base64_output": enable_base64_output
        }
        
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Google Nano Banana Text-to-Image job: {e}", exc_info=True)
            raise
    
    async def submit_alibaba_wan_2_5_text_to_image(
        self,
        prompt: str,
        size: str = "1024*1024",
        enable_prompt_expansion: bool = False,
        negative_prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit an Alibaba Wan 2.5 Text-to-Image job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            size: Image size in pixels (width*height), default: "1024*1024", range: 768 ~ 1440 per dimension
            enable_prompt_expansion: If true, the prompt optimizer will be enabled
            negative_prompt: Optional negative prompt for generation
            seed: Random seed (-1 to 2147483647, -1 means random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Alibaba Wan 2.5 Text-to-Image job: size={size}, enable_prompt_expansion={enable_prompt_expansion}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        
        url = f"{self.base_url}/alibaba/wan-2.5/text-to-image"
        
        payload = {
            "prompt": prompt,
            "size": size,
            "enable_prompt_expansion": enable_prompt_expansion,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Alibaba Wan 2.5 Text-to-Image job: {e}", exc_info=True)
            raise
    
    async def submit_flux_1_1_pro_ultra_text_to_image(
        self,
        prompt: str,
        size: str = "1024*1024",
        negative_prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit a Flux 1.1 Pro Ultra Text-to-Image job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            size: Image size in pixels (width*height), default: "1024*1024"
            negative_prompt: Optional negative prompt for generation
            seed: Random seed (-1 to 2147483647, -1 means random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Flux 1.1 Pro Ultra Text-to-Image job: size={size}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        
        url = f"{self.base_url}/wavespeed-ai/flux-1.1-pro-ultra"
        
        payload = {
            "prompt": prompt,
            "size": size,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Flux 1.1 Pro Ultra Text-to-Image job: {e}", exc_info=True)
            raise
    
    async def submit_stability_ai_stable_diffusion_3_5_large_turbo_text_to_image(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        aspect_ratio: str = "1:1",
        seed: int = -1,
        enable_base64_output: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Stability AI Stable Diffusion 3.5 Large Turbo Text-to-Image job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            image_url: Optional image URL for image-to-image generation
            aspect_ratio: Aspect ratio (1:1, 3:4, 4:3, 16:9, 9:16) - default: "1:1"
            seed: Random seed (-1 to 2147483647, -1 means random)
            enable_base64_output: If true, return base64 encoded output
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Stability AI Stable Diffusion 3.5 Large Turbo Text-to-Image job: aspect_ratio={aspect_ratio}, seed={seed}, image_url={'provided' if image_url else 'none'}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/stability-ai/stable-diffusion-3.5-large-turbo"
        
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
            "enable_base64_output": enable_base64_output
        }
        
        if image_url:
            payload["image"] = image_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Stability AI Stable Diffusion 3.5 Large Turbo Text-to-Image job: {e}", exc_info=True)
            raise
    
    async def submit_google_nano_banana_pro_edit(
        self,
        prompt: str,
        images: list,
        aspect_ratio: Optional[str] = None,
        resolution: str = "1k",
        output_format: str = "png",
        enable_sync_mode: bool = False,
        enable_base64_output: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Google Nano Banana Pro Edit job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for editing (required)
            images: List of image URLs (1-10 items) for editing (required)
            aspect_ratio: Aspect ratio (1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
            resolution: Resolution (1k, 2k, 4k) - default: "1k"
            output_format: Output format (png, jpeg) - default: "png"
            enable_sync_mode: If true, wait for result before returning
            enable_base64_output: If true, return base64 encoded output
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Nano Banana Pro Edit job: resolution={resolution}, output_format={output_format}, images_count={len(images)}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/google/nano-banana-pro/edit"
        
        payload = {
            "prompt": prompt,
            "images": images,
            "resolution": resolution,
            "output_format": output_format,
            "enable_sync_mode": enable_sync_mode,
            "enable_base64_output": enable_base64_output
        }
        
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Google Nano Banana Pro Edit job: {e}", exc_info=True)
            raise
    
    async def submit_google_nano_banana_edit(
        self,
        prompt: str,
        images: list,
        aspect_ratio: Optional[str] = None,
        output_format: str = "png",
        enable_sync_mode: bool = False,
        enable_base64_output: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Google Nano Banana Edit job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for editing (required)
            images: List of image URLs (1-10 items) for editing (required)
            aspect_ratio: Aspect ratio (1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9)
            output_format: Output format (png, jpeg) - default: "png"
            enable_sync_mode: If true, wait for result before returning
            enable_base64_output: If true, return base64 encoded output
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Google Nano Banana Edit job: output_format={output_format}, images_count={len(images)}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/google/nano-banana/edit"
        
        payload = {
            "prompt": prompt,
            "images": images,
            "output_format": output_format,
            "enable_sync_mode": enable_sync_mode,
            "enable_base64_output": enable_base64_output
        }
        
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Google Nano Banana Edit job: {e}", exc_info=True)
            raise
    
    async def submit_flux_kontext_max(
        self,
        prompt: str,
        image_url: str,
        aspect_ratio: Optional[str] = None,
        guidance_scale: float = 3.5,
        seed: int = -1,
        enable_sync_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a Flux Kontext Max job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for generation (required)
            image_url: URL of the input image (required)
            aspect_ratio: Aspect ratio (21:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 9:21)
            guidance_scale: Guidance scale (1.0 ~ 20.0), default: 3.5
            seed: Random seed (-1 to 2147483647, -1 means random)
            enable_sync_mode: If true, wait for result before returning
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Flux Kontext Max job: aspect_ratio={aspect_ratio}, guidance_scale={guidance_scale}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        
        url = f"{self.base_url}/wavespeed-ai/flux-kontext-max"
        
        payload = {
            "prompt": prompt,
            "image": image_url,
            "guidance_scale": guidance_scale,
            "enable_sync_mode": enable_sync_mode
        }
        
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        
        if seed is not None and seed != -1:
            payload["seed"] = seed
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Flux Kontext Max job: {e}", exc_info=True)
            raise
    
    async def submit_alibaba_wan_2_5_image_edit(
        self,
        prompt: str,
        image_url: str,
        size: str = "1024*1024",
        enable_prompt_expansion: bool = False,
        negative_prompt: Optional[str] = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        Submit an Alibaba Wan 2.5 Image Edit job to WaveSpeed AI.
        
        Args:
            prompt: The positive prompt for editing (required)
            image_url: URL of the input image (required)
            size: Image size in pixels (width*height), default: "1024*1024"
            enable_prompt_expansion: If true, the prompt optimizer will be enabled
            negative_prompt: Optional negative prompt for generation
            seed: Random seed (-1 to 2147483647, -1 means random)
        
        Returns:
            Dictionary with job information including task ID and status
        """
        if not self.api_key:
            raise ValueError("WaveSpeed API key not configured")
        
        logger.info(f"Submitting Alibaba Wan 2.5 Image Edit job: size={size}, enable_prompt_expansion={enable_prompt_expansion}, seed={seed}")
        logger.info(f"Prompt: {prompt}")
        if negative_prompt:
            logger.info(f"Negative prompt: {negative_prompt}")
        
        url = f"{self.base_url}/alibaba/wan-2.5/image-edit"
        
        payload = {
            "prompt": prompt,
            "image": image_url,
            "size": size,
            "enable_prompt_expansion": enable_prompt_expansion,
            "seed": seed
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"POST {url} with payload: {payload}")
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"WaveSpeed API response status: {response.status_code}")
                logger.info(f"WaveSpeed API response body: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"WaveSpeed job submitted successfully: task_id={result.get('data', {}).get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WaveSpeed API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            if status_code == 502:
                raise Exception("WaveSpeed API is temporarily unavailable. Please try again in a few moments.")
            elif status_code == 503:
                raise Exception("WaveSpeed API service is currently unavailable. Please try again later.")
            elif status_code == 429:
                raise Exception("Rate limit exceeded. Please wait a moment before trying again.")
            elif status_code >= 500:
                raise Exception("WaveSpeed API server error. Please try again later.")
            else:
                # Extract detailed error message if available
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message') or error_data.get('detail') or error_data.get('error', '')
                    if error_detail:
                        raise Exception(f"WaveSpeed API error: {status_code}. {error_detail}")
                except:
                    pass
                raise Exception(f"WaveSpeed API error: {status_code}. Please check your request and try again.")
        except httpx.RequestError as e:
            logger.error(f"WaveSpeed API request error: {e}")
            raise Exception(f"Failed to connect to WaveSpeed API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting Alibaba Wan 2.5 Image Edit job: {e}", exc_info=True)
            raise

