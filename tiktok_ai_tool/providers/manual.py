"""Provider thủ công: chuẩn bị ảnh 9:16 để bạn tải lên Hailuo (hoặc công cụ web khác).
Phần lớn gói miễn phí trên web không có API nên bước này làm tay."""
from pathlib import Path
from .base import VideoProvider, fit_image


class ManualProvider(VideoProvider):
    name = "manual"

    def generate(self, image_path, prompt, duration, out_dir: Path):
        fit_image(image_path, 720, 1280).save(out_dir / "input_9x16.png")
        self.log("\n>>> Làm tay trên Hailuo (trang chính thức: hailuoai.video):")
        self.log("    1) Chọn Image-to-Video, tải lên 'input_9x16.png' trong thư mục kết quả")
        self.log("    2) Dán nội dung 'prompt.txt' vào ô mô tả")
        self.log(f"    3) Chọn thời lượng {duration}s, tạo video, tải về rồi nhập lại bằng gui.py\n")
        return None
