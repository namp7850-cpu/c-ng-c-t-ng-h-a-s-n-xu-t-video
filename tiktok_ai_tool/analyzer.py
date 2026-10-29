"""Module 2: phân tích ảnh + kịch bản của bạn -> prompt hoàn chỉnh cho AI video."""
from dataclasses import dataclass

import llm
from config import Settings

# Giới hạn ô prompt trên web Hailuo: các nguồn nói 512 ký tự (web) hoặc 2000 (API).
# Chọn mức an toàn cho web. Sửa nếu bạn thấy giao diện của bạn cho phép nhiều hơn.
HAILUO_MAX_CHARS = 500
# Lệnh camera đã thấy trong tài liệu (viết trong ngoặc vuông, tối đa 3 lệnh, đặt ở đầu prompt).
HAILUO_CAMERA = ["Push in", "Pan left", "Pan right", "Zoom in", "Truck left", "Tracking", "Shake"]


@dataclass
class Analysis:
    description: str   # mô tả ảnh (do AI viết, rỗng nếu analyzer=none)
    prompt: str        # prompt cuối cùng đưa cho AI tạo video


INSTRUCTION = """Bạn là đạo diễn video ngắn. Có một ảnh làm khung hình đầu tiên và kịch bản của người dùng.
Nhiệm vụ:
1. Mô tả ngắn gọn ảnh (chủ thể, bối cảnh, ánh sáng, góc máy) bằng tiếng Việt.
2. Viết MỘT prompt tiếng Anh cho mô hình image-to-video, video dài {duration} giây.
   Prompt tập trung vào CHUYỂN ĐỘNG và diễn biến theo mốc thời gian, bám sát kịch bản,
   không mô tả lại toàn bộ ảnh, và không đưa thêm sự kiện ngoài kịch bản.{extra}
Kịch bản người dùng:
\"\"\"{script}\"\"\"
Trả về JSON đúng dạng: {{"description": "...", "prompt": "..."}}"""

HAILUO_EXTRA = """
   Quy tắc riêng cho Hailuo: prompt tối đa {n} ký tự (đếm cả khoảng trắng). Có thể mở đầu bằng tối đa 3 lệnh camera
   đặt trong ngoặc vuông, CHỈ chọn từ danh sách: {cams}. Ví dụ: "[Push in] A man in a boat ..." """


def analyze(image_path, script, mode, duration, cfg: Settings, target="generic") -> Analysis:
    if mode == "none":
        return Analysis(description="", prompt=script.strip())
    if mode in ("llm", "gemini"):
        return _llm(image_path, script, duration, cfg, target)
    raise ValueError(f"analyzer không hợp lệ: {mode}")


def check_prompt(prompt: str, target: str) -> list[str]:
    """Trả về danh sách cảnh báo (rỗng = ổn)."""
    warns = []
    if target == "hailuo":
        if len(prompt) > HAILUO_MAX_CHARS:
            warns.append(f"Prompt dài {len(prompt)} ký tự, vượt mức an toàn {HAILUO_MAX_CHARS} cho ô nhập của Hailuo. Hãy rút gọn.")
        if prompt.count("[") > 3:
            warns.append("Có hơn 3 lệnh camera trong ngoặc vuông; các nguồn nói tối đa 3.")
    return warns


def _llm(image_path, script, duration, cfg: Settings, target) -> Analysis:
    extra = ""
    if target == "hailuo":
        extra = HAILUO_EXTRA.format(n=HAILUO_MAX_CHARS - 50, cams=", ".join(HAILUO_CAMERA))
    text = llm.chat(cfg.vision_provider,
                    [{"role": "user", "content": INSTRUCTION.format(duration=duration, script=script, extra=extra)}],
                    image_path=image_path, json_mode=True, temperature=0.7).strip()
    try:
        data = llm.extract_json(text)
        return Analysis(data.get("description", ""), data["prompt"])
    except (ValueError, KeyError):
        return Analysis("", text or script.strip())
