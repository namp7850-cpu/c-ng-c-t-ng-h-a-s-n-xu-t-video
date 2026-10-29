"""Module 3: giao diện chung cho mọi nhà cung cấp tạo video."""
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image


def fit_image(path: str, width: int, height: int) -> Image.Image:
    """Cắt giữa và đổi cỡ ảnh cho vừa khung (mặc định dọc 9:16 cho TikTok)."""
    img = Image.open(path).convert("RGB")
    target = width / height
    w, h = img.size
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((width, height), Image.LANCZOS)


class VideoProvider(ABC):
    name = "base"

    def __init__(self, log=print):
        self.log = log

    @abstractmethod
    def generate(self, image_path: str, prompt: str, duration: int, out_dir: Path) -> Path | None:
        """Tạo video, trả về đường dẫn file mp4 (hoặc None nếu bước này làm thủ công)."""
