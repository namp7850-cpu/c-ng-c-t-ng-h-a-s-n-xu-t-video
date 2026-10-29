"""Provider chạy MIỄN PHÍ trên máy bạn: Wan 2.2 TI2V-5B qua thư viện diffusers.
Cần GPU NVIDIA. Mức VRAM tối thiểu khác nhau giữa các nguồn (8-24 GB), hãy thử
với WAN_CPU_OFFLOAD=1 và giảm WAN_WIDTH/WAN_HEIGHT/WAN_STEPS nếu hết bộ nhớ.
LƯU Ý: đoạn code này chưa được chạy thử trên GPU cụ thể của bạn."""
from pathlib import Path
from config import Settings
from .base import VideoProvider, fit_image


class WanLocalProvider(VideoProvider):
    name = "wan_local"

    def __init__(self, cfg: Settings, log=print):
        super().__init__(log)
        self.cfg = cfg
        self.pipe = None

    def _load(self):
        import torch
        from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
        vae = AutoencoderKLWan.from_pretrained(self.cfg.wan_model_id, subfolder="vae", torch_dtype=torch.float32)
        pipe = WanImageToVideoPipeline.from_pretrained(self.cfg.wan_model_id, vae=vae, torch_dtype=torch.bfloat16)
        if self.cfg.wan_cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
        self.pipe = pipe

    def generate(self, image_path, prompt, duration, out_dir: Path):
        from diffusers.utils import export_to_video
        if self.pipe is None:
            self._load()
        fps = 24
        num_frames = duration * fps + 1          # Wan cần số khung dạng 4k+1 (6s -> 145)
        num_frames = ((num_frames - 1) // 4) * 4 + 1
        image = fit_image(image_path, self.cfg.wan_width, self.cfg.wan_height)
        frames = self.pipe(
            image=image, prompt=prompt,
            height=self.cfg.wan_height, width=self.cfg.wan_width,
            num_frames=num_frames, guidance_scale=5.0,
            num_inference_steps=self.cfg.wan_steps,
        ).frames[0]
        out = out_dir / "video.mp4"
        export_to_video(frames, str(out), fps=fps)
        return out
