"""
Model configuration for different AI providers.
Defines capabilities, parameters, and API endpoints for each model.
"""
from typing import Dict, List, Optional, Any
from enum import Enum


class ModelProvider(str, Enum):
    """Supported AI model providers."""
    WAN_2_5 = "wan-2.5"
    WAN_2_1 = "wan-2.1"
    GOOGLE_VEO_3_1 = "google-veo-3.1"
    GOOGLE_VEO_3 = "google-veo-3"
    OPENAI_SORA_2 = "openai-sora-2"
    OPENAI_SORA_2_PRO = "openai-sora-2-pro"
    MINIMAX_HAILUO = "minimax-hailuo"
    MINIMAX_HAILUO_2_3_PRO = "minimax-hailuo-2.3-pro"
    KLING = "kling"
    KLING_V2_5_TURBO_PRO = "kling-v2.5-turbo-pro"
    SEEDANCE = "seedance"
    SEEDANCE_V1_PRO = "seedance-v1-pro"


class ModelConfig:
    """Configuration for a specific AI model."""
    
    def __init__(
        self,
        provider: ModelProvider,
        name: str,
        display_name: str,
        api_endpoint: str,
        supported_resolutions: List[str],
        supported_durations: List[int],
        supports_audio: bool = False,
        supports_negative_prompt: bool = False,
        supports_prompt_expansion: bool = False,
        credit_per_second: Dict[str, float] = None,  # Map resolution to credits per second (can be float for 2.5x scaling)
        default_resolution: str = "1280*720",
        default_duration: int = 5,
        description: str = "",
        icon: str = "/images/play-icon.svg",
        uses_aspect_ratio: bool = False,  # Some models use aspect_ratio instead of size
        supported_aspect_ratios: List[str] = None  # For models that use aspect_ratio
    ):
        self.provider = provider
        self.name = name
        self.display_name = display_name
        self.api_endpoint = api_endpoint
        self.supported_resolutions = supported_resolutions
        self.supported_durations = supported_durations
        self.supports_audio = supports_audio
        self.supports_negative_prompt = supports_negative_prompt
        self.supports_prompt_expansion = supports_prompt_expansion
        self.credit_per_second = credit_per_second or {}
        self.default_resolution = default_resolution
        self.default_duration = default_duration
        self.description = description
        self.icon = icon
        self.uses_aspect_ratio = uses_aspect_ratio
        self.supported_aspect_ratios = supported_aspect_ratios or []
    
    def get_credit_cost(self, resolution: str, duration: int) -> int:
        """Calculate credit cost for given resolution and duration.
        
        Uses 2.5x scaling: $0.10 = 2.5 credits, $1 = 10 credits
        
        Some models have fixed pricing per video (e.g., Veo 3: $3.2 with audio, $1.2 without)
        Wan 2.5 uses complex pricing: base 1080p 10s = 32 credits, 10% reduction per second, 20% reduction per resolution step
        """
        # Special handling for models with custom pricing (matching image-to-video pricing)
        if self.name == "google-veo-3":
            # Veo 3: duration-based pricing (same as google-veo-3-fast in image-to-video)
            # Pricing: 4s=32, 6s=50, 8s=64 credits
            credit_by_duration = {4: 32, 6: 50, 8: 64}
            return credit_by_duration.get(duration, 32)  # Default to 32 if duration not found
        elif self.name == "google-veo-3.1":
            # Veo 3.1: duration-based pricing (same as google-veo-3.1-fast in image-to-video)
            # Pricing: 4s=32, 6s=50, 8s=64 credits (but text-to-video supports 5s, 10s)
            # For text-to-video, we'll use the same pricing structure
            credit_by_duration = {4: 32, 5: 32, 6: 50, 8: 64, 10: 64}  # Map to closest values
            return credit_by_duration.get(duration, 32)  # Default to 32 if duration not found
        elif self.name == "openai-sora-2":
            # Sora 2: non-linear pricing (same as image-to-video)
            # Pricing: 4s=8, 8s=16, 12s=22 credits
            credit_by_duration = {4: 8, 8: 16, 12: 22}
            return credit_by_duration.get(duration, 8)  # Default to 8 if duration not found
        elif self.name == "openai-sora-2-pro":
            # Sora 2 Pro: non-linear pricing based on resolution and duration (same as image-to-video)
            # Pricing: 720p: 4s=22, 8s=44, 12s=66 | 1080p: 4s=40, 8s=80, 12s=120
            credit_by_resolution = {
                "720p": {4: 22, 8: 44, 12: 66},
                "1080p": {4: 40, 8: 80, 12: 120}
            }
            # Determine resolution tier
            width, height = map(int, resolution.split('*'))
            # 720p: both dimensions <= 1280, 1080p: either dimension > 1280
            if width <= 1280 and height <= 1280:  # 720p
                tier = "720p"
            else:  # 1080p
                tier = "1080p"
            resolution_pricing = credit_by_resolution.get(tier, {})
            return resolution_pricing.get(duration, 22)  # Default to 22 if not found
        elif self.name == "kling-v2.5-turbo-pro":
            # Kling V2.5 Turbo Pro: non-linear pricing (same as image-to-video)
            # Pricing: 5s=7, 10s=20 credits
            credit_by_duration = {5: 7, 10: 20}
            return credit_by_duration.get(duration, 7)  # Default to 7 if duration not found
        elif self.name == "minimax-hailuo-2.3-pro":
            # Hailuo 2.3 Pro: fixed pricing (same as hailuo-2.3-i2v-pro in image-to-video)
            # Pricing: 12 credits per job (fixed 5s, 1080p)
            return 12  # Fixed cost per video
        elif self.name == "wan-2.5":
            # Wan 2.5: complex pricing based on base (1080p 10s = 32 credits)
            # Base: 1080p 10s = 32 credits
            # Each second reduction: multiply by 0.9 (10% reduction)
            # Resolution reduction: 720p = 0.8 of 1080p, 480p = 0.64 of 1080p (20% reduction each step)
            base_credit = 32
            resolution_multiplier = {
                "1080p": 1.0,
                "720p": 0.8,   # 20% reduction from 1080p
                "480p": 0.64   # 20% reduction from 720p (0.8 * 0.8 = 0.64)
            }
            # Duration multiplier: 0.9^(10 - duration)
            duration_multiplier = 0.9 ** (10 - duration)
            
            # Determine resolution tier
            width, height = map(int, resolution.split('*'))
            if width <= 832 or height <= 832:  # 480p
                tier = "480p"
            elif width <= 1280 or height <= 1280:  # 720p
                tier = "720p"
            else:  # 1080p
                tier = "1080p"
            
            res_mult = resolution_multiplier.get(tier, 1.0)
            return int(round(base_credit * res_mult * duration_multiplier))
        
        # Determine resolution tier
        width, height = map(int, resolution.split('*'))
        
        if width <= 832 or height <= 832:  # 480p
            tier = "480p"
        elif width <= 1280 or height <= 1280:  # 720p
            tier = "720p"
        else:  # 1080p
            tier = "1080p"
        
        credit_per_sec = self.credit_per_second.get(tier, 2.5)  # Default 2.5 credits/sec ($0.10/s)
        return int(credit_per_sec * duration)
    
    def is_resolution_supported(self, resolution: str) -> bool:
        """Check if a resolution is supported by this model."""
        return resolution in self.supported_resolutions
    
    def is_duration_supported(self, duration: int) -> bool:
        """Check if a duration is supported by this model."""
        return duration in self.supported_durations


# Model configurations
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "google-veo-3.1": ModelConfig(
        provider=ModelProvider.GOOGLE_VEO_3_1,
        name="google-veo-3.1",
        display_name="Google Veo 3.1",
        api_endpoint="/google/veo3.1/text-to-video",  # Correct endpoint per WaveSpeed docs
        supported_resolutions=["1280*720", "720*1280", "1920*1080", "1080*1920"],  # For display
        supported_durations=[4, 6, 8],  # Valid durations per API: 4, 6, or 8 seconds
        supports_audio=False,  # Veo 3.1 generates audio automatically via generate_audio parameter
        supports_negative_prompt=True,
        supports_prompt_expansion=False,
        credit_per_second={"720p": 4, "1080p": 6},  # Estimated pricing
        default_resolution="1280*720",
        default_duration=8,  # Default to 8s per API docs
        description="Precision video with sound control",
        icon="/images/logos/icons8-google-logo-48.svg",
        uses_aspect_ratio=True,  # Veo 3.1 uses aspect_ratio instead of size
        supported_aspect_ratios=["16:9", "9:16"]  # Valid aspect ratios per API
    ),
    "wan-2.5": ModelConfig(
        provider=ModelProvider.WAN_2_5,
        name="wan-2.5",
        display_name="Wan 2.5",
        api_endpoint="/alibaba/wan-2.5/text-to-video",
        supported_resolutions=["832*480", "480*832", "1280*720", "720*1280", "1920*1080", "1080*1920"],
        supported_durations=[5, 10],
        supports_audio=True,
        supports_negative_prompt=True,
        supports_prompt_expansion=True,
        credit_per_second={"480p": 5, "720p": 10, "1080p": 15},
        default_resolution="1280*720",
        default_duration=5,
        description="High-quality text-to-video with audio sync",
        icon="/images/logos/wan-logo.svg"
    ),
    "openai-sora-2": ModelConfig(
        provider=ModelProvider.OPENAI_SORA_2,
        name="openai-sora-2",
        display_name="OpenAI Sora 2",
        api_endpoint="/openai/sora-2/text-to-video",
        supported_resolutions=["1280*720", "720*1280"],
        supported_durations=[4, 8, 12],
        supports_audio=False,
        supports_negative_prompt=False,  # Sora 2 does not support negative prompts
        supports_prompt_expansion=False,
        credit_per_second={"720p": 2.5},  # $0.10/s = 2.5 credits/s
        default_resolution="720*1280",
        default_duration=4,
        description="State-of-the-art text-to-video with synchronized audio",
        icon="/images/logos/sora-color.svg"
    ),
    "openai-sora-2-pro": ModelConfig(
        provider=ModelProvider.OPENAI_SORA_2_PRO,
        name="openai-sora-2-pro",
        display_name="OpenAI Sora 2 Pro",
        api_endpoint="/openai/sora-2/text-to-video-pro",
        supported_resolutions=["1280*720", "720*1280", "1792*1024", "1024*1792"],
        supported_durations=[4, 8, 12],
        supports_audio=False,
        supports_negative_prompt=False,  # Sora 2 Pro does not support negative prompts
        supports_prompt_expansion=False,
        credit_per_second={"720p": 3.75, "1080p": 6.25},  # Pro version - higher quality, higher cost
        default_resolution="1280*720",
        default_duration=4,
        description="Professional-grade Sora 2 with enhanced quality and control",
        icon="/images/logos/sora-color.svg"
    ),
    "minimax-hailuo": ModelConfig(
        provider=ModelProvider.MINIMAX_HAILUO,
        name="minimax-hailuo",
        display_name="Minimax Hailuo",
        api_endpoint="/minimax/hailuo/text-to-video",
        supported_resolutions=["832*480", "480*832", "1280*720", "720*1280"],
        supported_durations=[5, 10],
        supports_audio=False,
        supports_negative_prompt=False,
        supports_prompt_expansion=False,
        credit_per_second={"480p": 1, "720p": 2},  # Most affordable
        default_resolution="1280*720",
        default_duration=5,
        description="High-dynamic, VFX-ready, fastest and most affordable",
        icon="/images/logos/hailuo.svg"
    ),
    "minimax-hailuo-2.3-pro": ModelConfig(
        provider=ModelProvider.MINIMAX_HAILUO_2_3_PRO,
        name="minimax-hailuo-2.3-pro",
        display_name="Minimax Hailuo 2.3 Pro",
        api_endpoint="/minimax/hailuo-2.3/t2v-pro",
        supported_resolutions=["1920*1080", "1080*1920"],  # Fixed 1080p only
        supported_durations=[5],  # Fixed 5 seconds only
        supports_audio=False,
        supports_negative_prompt=False,  # Not supported
        supports_prompt_expansion=True,  # Supported with default true
        credit_per_second={"1080p": 12.25},  # $0.49 = 12.25 credits (fixed price per video)
        default_resolution="1920*1080",
        default_duration=5,
        description="Professional Hailuo model with enhanced quality - 5s 1080p videos",
        icon="/images/logos/hailuo.svg"
    ),
    "kling-v2.5-turbo-pro": ModelConfig(
        provider=ModelProvider.KLING_V2_5_TURBO_PRO,
        name="kling-v2.5-turbo-pro",
        display_name="Kling v2.5 Turbo Pro",
        api_endpoint="/kwaivgi/kling-v2.5-turbo-pro/text-to-video",
        supported_resolutions=["1280*720", "720*1280", "1920*1080", "1080*1920"],  # For display
        supported_durations=[5, 10],
        supports_audio=False,
        supports_negative_prompt=True,
        supports_prompt_expansion=False,
        credit_per_second={"720p": 1.75, "1080p": 1.75},  # $0.07/s = 1.75 credits/s ($0.35 for 5s, $0.70 for 10s)
        default_resolution="1280*720",
        default_duration=5,
        description="Turbo Pro version with enhanced speed and quality",
        icon="/images/logos/kling-color.svg",
        uses_aspect_ratio=True,
        supported_aspect_ratios=["16:9", "9:16", "1:1"]
    ),
    "seedance": ModelConfig(
        provider=ModelProvider.SEEDANCE,
        name="seedance",
        display_name="Seedance v1 Lite",
        api_endpoint="/bytedance/seedance-v1-lite-t2v-1080p",
        supported_resolutions=["1920*1080", "1080*1920"],  # Fixed 1080p only
        supported_durations=[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        supports_audio=False,
        supports_negative_prompt=False,  # Seedance v1 Lite does not support negative prompts
        supports_prompt_expansion=False,
        credit_per_second={"1080p": 3},  # Estimated pricing
        default_resolution="1920*1080",
        default_duration=5,
        description="Cinematic, multi-shot video creation - 1080p videos",
        icon="/images/logos/cropped-Seedance.svg",
        uses_aspect_ratio=True,
        supported_aspect_ratios=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]
    ),
    "seedance-v1-pro": ModelConfig(
        provider=ModelProvider.SEEDANCE_V1_PRO,
        name="seedance-v1-pro",
        display_name="Seedance v1 Pro",
        api_endpoint="/bytedance/seedance-v1-pro-t2v-1080p",
        supported_resolutions=["1920*1080", "1080*1920"],  # For display purposes
        supported_durations=[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        supports_audio=False,
        supports_negative_prompt=False,  # Seedance v1 Pro does not support negative prompts
        supports_prompt_expansion=False,
        credit_per_second={"1080p": 7.5},  # Pro version, 1080p only
        default_resolution="1920*1080",
        default_duration=5,
        description="Professional 1080p cinematic video generation",
        icon="/images/logos/cropped-Seedance.svg",
        uses_aspect_ratio=True,
        supported_aspect_ratios=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]
    ),
}


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model."""
    return MODEL_CONFIGS.get(model_name)


def get_all_models() -> List[ModelConfig]:
    """Get all available model configurations."""
    return list(MODEL_CONFIGS.values())


def get_model_by_provider(provider: ModelProvider) -> Optional[ModelConfig]:
    """Get model configuration by provider enum."""
    for config in MODEL_CONFIGS.values():
        if config.provider == provider:
            return config
    return None

