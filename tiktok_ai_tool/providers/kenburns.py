"""Provider miễn phí 100%, KHÔNG dùng AI: zoom chậm vào ảnh bằng ffmpeg.
Dùng để chạy thử toàn bộ quy trình mà không tốn tiền hay cần GPU."""
import subprocess
from pathlib import Path
from .base import VideoProvider, fit_image


class KenBurnsProvider(VideoProvider):
    name = "kenburns"

    def generate(self, image_path, prompt, duration, out_dir: Path):
        tmp = out_dir / "_frame.png"
        fit_image(image_path, 2160, 3840).save(tmp)
        out = out_dir / "video.mp4"
        fps = 30
        frames = duration * fps
        vf = (f"zoompan=z='min(zoom+0.0007,1.25)':d={frames}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
               "-vf", vf, "-t", str(duration), "-pix_fmt", "yuv420p", str(out)]
        subprocess.run(cmd, check=True)
        tmp.unlink(missing_ok=True)
        return out
