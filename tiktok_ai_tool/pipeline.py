"""Lõi dùng chung cho CLI và giao diện cửa sổ."""
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from analyzer import analyze, check_prompt
from config import Settings
from providers import get_provider


@dataclass
class Run:
    out_dir: Path
    image: str
    script: str
    analyzer: str
    target: str
    duration: int
    description: str = ""
    prompt: str = ""
    provider: str = ""
    video: str | None = None


def prepare(image, script, analyzer, duration, target, out_root, cfg: Settings) -> Run:
    out_dir = Path(out_root) / time.strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    res = analyze(image, script, analyzer, duration, cfg, target)
    run = Run(out_dir, image, script, analyzer, target, duration, res.description, res.prompt)
    save(run)
    return run


def save(run: Run, prompt: str | None = None):
    """Ghi prompt.txt và meta.json (gọi lại sau khi bạn sửa prompt)."""
    if prompt is not None:
        run.prompt = prompt
    (run.out_dir / "prompt.txt").write_text(run.prompt, encoding="utf-8")
    meta = asdict(run)
    meta["out_dir"] = str(run.out_dir)
    (run.out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def render(run: Run, provider_name: str, cfg: Settings, log=print, ask=None):
    run.provider = provider_name
    video = get_provider(provider_name, cfg, log, ask).generate(run.image, run.prompt, run.duration, run.out_dir)
    run.video = str(video) if video else None
    save(run)
    return video


def import_video(run: Run, src: str) -> str:
    """Nhập video đã tải từ Hailuo về thư mục kết quả; trả về chuỗi thông tin."""
    dst = run.out_dir / "video.mp4"
    shutil.copy2(src, dst)
    run.video = str(dst)
    save(run)
    info = f"Đã lưu: {dst}"
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height:format=duration",
                            "-of", "default=nw=1", str(dst)], capture_output=True, text=True)
        info += "\n" + r.stdout.strip().replace("\n", ", ")
    return info


def warnings(run: Run) -> list[str]:
    return check_prompt(run.prompt, run.target)
