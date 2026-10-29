"""Tạo video TỰ ĐỘNG bằng API chính thức của MiniMax (Hailuo H3). Trả phí theo từng video (xem bảng giá dưới).
Quy trình đúng theo tài liệu: POST /v2/video_generation -> hỏi trạng thái -> tải video từ content.url."""
import base64
import io
import time
from pathlib import Path

import requests

from config import Settings
from .base import VideoProvider, fit_image

# USD mỗi giây video đầu ra (trang giá platform.minimax.io, tra cứu 29/10/2026 - hãy kiểm tra lại trước khi nạp tiền)
PRICE_PER_SEC = {
    ("MiniMax-H3", "2K"): 0.13, ("MiniMax-H3", "768P"): 0.08,
    ("MiniMax-H3-Highspeed", "768P"): 0.06,
    ("MiniMax-H3-Lite", "768P"): 0.04, ("MiniMax-H3-Lite", "480P"): 0.025,
    ("MiniMax-H3-Max", "768P"): 0.08, ("MiniMax-H3-Max", "480P"): 0.05,
}
MIN_DURATION = {"MiniMax-H3-Max": 5}  # các model khác tối thiểu 4 giây, tối đa 15


def estimate_cost(model: str, resolution: str, duration: int) -> float:
    """Chi phí video đầu ra. Ảnh đầu vào đầu tiên miễn phí theo bảng giá."""
    key = (model, resolution)
    if key not in PRICE_PER_SEC:
        raise ValueError(f"Tổ hợp model/độ phân giải không hợp lệ: {model} + {resolution}. "
                         f"Hợp lệ: {', '.join(f'{m}+{r}' for m, r in PRICE_PER_SEC)}")
    return round(PRICE_PER_SEC[key] * duration, 3)


class MiniMaxAPIProvider(VideoProvider):
    name = "minimax_api"

    def __init__(self, cfg: Settings, log=print):
        super().__init__(log)
        self.cfg = cfg

    def check(self, duration: int):
        """Kiểm tra cấu hình và chặn nếu vượt hạn mức chi tiêu. Trả về chi phí ước tính."""
        c = self.cfg
        if not c.minimax_key:
            raise RuntimeError("Thiếu MINIMAX_API_KEY trong .env (tạo tại platform.minimax.io, mục API Keys, và nạp một ít tiền).")
        if not (MIN_DURATION.get(c.minimax_model, 4) <= duration <= 15):
            raise ValueError(f"Thời lượng {duration}s không hợp lệ cho {c.minimax_model} (cho phép {MIN_DURATION.get(c.minimax_model, 4)}-15s).")
        cost = estimate_cost(c.minimax_model, c.minimax_resolution, duration)
        if cost > c.max_usd_per_run:
            raise RuntimeError(f"Chi phí ước tính ${cost} vượt hạn mức MAX_USD_PER_RUN=${c.max_usd_per_run}. Nâng hạn mức trong .env nếu bạn chắc chắn.")
        return cost

    def generate(self, image_path, prompt, duration, out_dir: Path):
        c = self.cfg
        cost = self.check(duration)
        buf = io.BytesIO()
        fit_image(image_path, 720, 1280).save(buf, "JPEG", quality=92)
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        payload = {
            "model": c.minimax_model,
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_uri}, "role": "first_frame"},
            ],
            "resolution": c.minimax_resolution,
            "duration": duration,
        }
        headers = {"Authorization": f"Bearer {c.minimax_key}", "Content-Type": "application/json"}
        base = c.minimax_base.rstrip("/")
        self.log(f"Gửi yêu cầu tới MiniMax ({c.minimax_model}, {c.minimax_resolution}, {duration}s). Ước tính ≈ ${cost}")
        r = requests.post(base + "/v2/video_generation", headers=headers, json=payload, timeout=120)
        self._raise_for(r)
        task_id = r.json()["task_id"]
        self.log(f"Đã nhận task {task_id}, đang chờ tạo video...")

        deadline = time.time() + c.poll_timeout
        last = None
        while time.time() < deadline:
            time.sleep(c.poll_seconds)
            q = requests.get(f"{base}/v2/query/video_generation/{task_id}", headers=headers, timeout=60)
            self._raise_for(q)
            task = q.json()["task"]
            status = task["status"]
            if status != last:
                self.log(f"Trạng thái: {status}")
                last = status
            if status == "succeeded":
                url = task["content"]["url"]
                v = requests.get(url, timeout=300)
                v.raise_for_status()
                out = out_dir / "video.mp4"
                out.write_bytes(v.content)
                (out_dir / "task.json").write_text(__import__("json").dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
                self.log(f"Đã tải video: {out}")
                return out
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"MiniMax báo {status}: {task.get('error')}")
        raise TimeoutError(f"Quá {int(c.poll_timeout)}s mà chưa xong. Task {task_id} có thể vẫn đang chạy; kiểm tra trên platform.minimax.io.")

    @staticmethod
    def _raise_for(r):
        if r.status_code < 400:
            return
        try:
            msg = r.json().get("error", {}).get("message", r.text[:300])
        except ValueError:
            msg = r.text[:300]
        hints = {401: "Khoá API sai hoặc thiếu.", 402: "Không đủ số dư, hãy nạp thêm tiền trên platform.minimax.io.",
                 422: "Nội dung bị coi là nhạy cảm, hãy sửa kịch bản/ảnh.", 429: "Gọi quá nhanh, thử lại sau."}
        raise RuntimeError(f"MiniMax lỗi HTTP {r.status_code}: {msg}. {hints.get(r.status_code, '')}")
