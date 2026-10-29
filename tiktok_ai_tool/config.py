"""Module cấu hình: đọc .env và biến môi trường."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    vision_provider: str = os.getenv("VISION_PROVIDER", "gemini")   # AI nhìn ảnh (khoá trong llm_providers.json)
    writer_provider: str = os.getenv("WRITER_PROVIDER", "gemini")   # AI viết kịch bản
    minimax_key: str = os.getenv("MINIMAX_API_KEY", "")
    minimax_base: str = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
    minimax_model: str = os.getenv("MINIMAX_MODEL", "MiniMax-H3-Lite")
    minimax_resolution: str = os.getenv("MINIMAX_RESOLUTION", "480P")
    max_usd_per_run: float = float(os.getenv("MAX_USD_PER_RUN", "0.50"))
    poll_seconds: float = float(os.getenv("POLL_SECONDS", "10"))
    poll_timeout: float = float(os.getenv("POLL_TIMEOUT", "900"))
    wan_model_id: str = os.getenv("WAN_MODEL_ID", "Wan-AI/Wan2.2-TI2V-5B-Diffusers")
    wan_width: int = int(os.getenv("WAN_WIDTH", "704"))
    wan_height: int = int(os.getenv("WAN_HEIGHT", "1280"))
    wan_steps: int = int(os.getenv("WAN_STEPS", "30"))
    wan_cpu_offload: bool = os.getenv("WAN_CPU_OFFLOAD", "1") == "1"
    hailuo_url: str = os.getenv("HAILUO_URL", "https://hailuoai.video")
