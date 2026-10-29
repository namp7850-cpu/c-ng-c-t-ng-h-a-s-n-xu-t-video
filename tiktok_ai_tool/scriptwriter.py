"""Biên kịch video 6 giây: tạo nhiều phương án có logic nhân quả, có hook, có cú lật,
rồi để chính AI tự chấm điểm. Chạy được với bất kỳ nhà cung cấp trong llm_providers.json."""
import time
from pathlib import Path

import llm
from analyzer import HAILUO_CAMERA, HAILUO_MAX_CHARS

SYSTEM = """Bạn là biên kịch video ngắn viral cho TikTok, chuyên kịch bản 6 giây dùng cho AI image-to-video.
Nguyên tắc BẮT BUỘC (đây là thứ phân biệt kịch bản hay với kịch bản dở):
1. HOOK: khung hình đầu đã có sẵn (ảnh). 1-2 giây đầu phải khiến người xem tự hỏi "chuyện gì sắp xảy ra?".
2. LOGIC NHÂN QUẢ: mỗi nhịp là hệ quả trực tiếp của nhịp trước. Không có sự kiện tự dưng xuất hiện.
   Viết thành chuỗi: A khiến B, B khiến C.
3. CÚ LẬT (twist) ở giây 3-5, và phải được GÀI MẦM từ trước (một chi tiết nhìn thấy ở đầu video làm cú lật hợp lý khi nhìn lại).
4. ĐƠN GIẢN ĐỂ AI LÀM ĐƯỢC: 1 chủ thể chính, 1 hành động chính, tối đa 1 thay đổi camera. Không cảnh đông người, không chữ, không lời thoại.
5. KHUNG CUỐI gợi ý vòng lặp hoặc để lại câu hỏi, để người xem muốn xem lại.
6. Chỉ viết điều NHÌN THẤY ĐƯỢC và hợp vật lý. Không viết cảm xúc trừu tượng.
7. Prompt tiếng Anh cho mô hình video: tối đa {maxc} ký tự, mô tả CHUYỂN ĐỘNG theo thứ tự thời gian, không mô tả lại toàn bộ ảnh.{cams}
Chỉ trả về JSON hợp lệ, không thêm chữ nào khác."""

CAMS = " Có thể mở đầu bằng tối đa 3 lệnh camera trong ngoặc vuông, chỉ chọn từ: {c}."

USER = """Ý tưởng/kịch bản thô của người dùng:
\"\"\"{idea}\"\"\"
Mô tả ảnh khung đầu: {desc}
Độ dài video: {dur} giây.

Hãy tạo {n} phương án KHÁC NHAU rõ rệt về cú lật. Với mỗi phương án tự chấm điểm nghiêm khắc (1-10) và nêu điểm yếu thật.
Trả về JSON dạng:
{{"options":[{{"title":"...","hook":"...","logic_chain":"A -> B -> C -> D","twist":"...","loop_end":"...",
"beats":[{{"t":"0-1s","action":"..."}}],"hailuo_prompt":"English prompt <= {maxc} chars",
"scores":{{"logic":0,"hook":0,"feasibility":0}},"weakness":"..."}}],"best_index":0}}"""


def describe(image_path: str, provider: str) -> str:
    """Nhờ mô hình có khả năng nhìn ảnh mô tả khung đầu (tiếng Việt, ngắn gọn)."""
    msg = [{"role": "user", "content": "Mô tả ngắn gọn ảnh này bằng tiếng Việt trong 3 câu: chủ thể, bối cảnh, ánh sáng, góc máy. Không bịa chi tiết không có trong ảnh."}]
    return llm.chat(provider, msg, image_path=image_path, temperature=0.2, max_tokens=400).strip()


def write_options(idea: str, desc: str, provider: str, n=3, duration=6, hailuo=True) -> dict:
    system = SYSTEM.format(maxc=HAILUO_MAX_CHARS - 50,
                           cams=CAMS.format(c=", ".join(HAILUO_CAMERA)) if hailuo else "")
    user = USER.format(idea=idea.strip(), desc=desc or "(không có ảnh)", dur=duration, n=n, maxc=HAILUO_MAX_CHARS - 50)
    raw = llm.chat(provider, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   json_mode=True, temperature=0.9, max_tokens=3000)
    data = llm.extract_json(raw)
    for o in data.get("options", []):
        o["prompt_len"] = len(o.get("hailuo_prompt", ""))
        o["too_long"] = o["prompt_len"] > HAILUO_MAX_CHARS
    return data


def best(data: dict) -> dict:
    opts = data.get("options", [])
    if not opts:
        raise ValueError("AI không trả về phương án nào")
    i = data.get("best_index", 0)
    return opts[i if isinstance(i, int) and 0 <= i < len(opts) else 0]


def format_option(o: dict) -> str:
    lines = [f"■ {o.get('title','(không tên)')}", f"Hook: {o.get('hook','')}", f"Chuỗi logic: {o.get('logic_chain','')}",
             f"Cú lật: {o.get('twist','')}", f"Kết/vòng lặp: {o.get('loop_end','')}", "Nhịp:"]
    lines += [f"  {b.get('t','')}: {b.get('action','')}" for b in o.get("beats", [])]
    sc = o.get("scores", {})
    lines += [f"Tự chấm: logic {sc.get('logic','?')}, hook {sc.get('hook','?')}, khả thi {sc.get('feasibility','?')}",
              f"Điểm yếu: {o.get('weakness','')}",
              f"Prompt ({o.get('prompt_len', 0)} ký tự{' - QUÁ DÀI' if o.get('too_long') else ''}): {o.get('hailuo_prompt','')}"]
    return "\n".join(lines)


def compare(idea: str, desc: str, providers: list[str], out_dir: str, n=2, duration=6) -> Path:
    """Chạy CÙNG một đề bài trên nhiều AI, ghi file so sánh để bạn tự chọn AI viết hay nhất."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / f"so_sanh_{time.strftime('%Y%m%d_%H%M%S')}.md"
    parts = [f"# So sánh AI viết kịch bản\n\nĐề bài: {idea}\n\nMô tả ảnh: {desc or '(không)'}\n"]
    for p in providers:
        parts.append(f"\n## {p}\n")
        try:
            data = write_options(idea, desc, p, n=n, duration=duration)
            parts.append("```\n" + "\n\n".join(format_option(o) for o in data.get("options", [])) + "\n```")
        except Exception as e:  # một nhà cung cấp lỗi không làm hỏng cả bảng so sánh
            parts.append(f"LỖI: {e}")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
