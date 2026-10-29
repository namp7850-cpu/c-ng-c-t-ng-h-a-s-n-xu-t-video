"""Tự động hoá TRÌNH DUYỆT trên trang web Hailuo (dùng credit miễn phí của tài khoản bạn).
CẢNH BÁO TRUNG THỰC:
- Mình CHƯA chạy thử với trang thật (không đăng nhập được), nên các bộ chọn (selector) có thể cần chỉnh trong hailuo_selectors.json.
- Tự động hoá giao diện web có thể trái điều khoản dịch vụ của Hailuo (mình chưa kiểm tra điều khoản). Rủi ro: bị hạn chế tài khoản.
- Công cụ KHÔNG nhập mật khẩu hộ, KHÔNG vượt captcha/xác minh: bạn tự đăng nhập một lần trong cửa sổ trình duyệt riêng.
- Chỉ chạy từng video một, không chạy hàng loạt.
Cài: pip install playwright  &&  playwright install chromium"""
import json
from pathlib import Path

from config import Settings
from .base import VideoProvider, fit_image

PROFILE_DIR = Path(".hailuo_profile")   # lưu phiên đăng nhập; KHÔNG chia sẻ/đưa lên GitHub
SELECTORS = Path(__file__).resolve().parent.parent / "hailuo_selectors.json"


class HailuoWebProvider(VideoProvider):
    name = "hailuo_web"

    def __init__(self, cfg: Settings, log=print, ask=None):
        super().__init__(log)
        self.cfg = cfg
        self.ask = ask or (lambda msg: input(msg + "\n(Nhấn Enter khi xong) "))

    def generate(self, image_path, prompt, duration, out_dir: Path):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Chưa cài playwright. Chạy: pip install playwright && playwright install chromium")
        sel = json.loads(SELECTORS.read_text(encoding="utf-8"))
        img = out_dir / "input_9x16.png"
        fit_image(image_path, 720, 1280).save(img)

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=False, accept_downloads=True)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                page.goto(sel.get("start_url") or self.cfg.hailuo_url, timeout=60000)
                self.ask("Trong cửa sổ trình duyệt vừa mở: đăng nhập (nếu cần), xử lý mọi bước xác minh, "
                         "rồi mở màn hình tạo video từ ảnh (Image-to-Video).")
                page.set_input_files(sel["file_input"], str(img))
                self.log("Đã tải ảnh lên.")
                page.fill(sel["prompt_box"], prompt)
                before = set(page.eval_on_selector_all(sel["result_video"], "els => els.map(e => e.currentSrc || e.src)"))
                clicked = False
                for t in sel["generate_button_texts"]:
                    btn = page.get_by_role("button", name=t)
                    if btn.count():
                        btn.first.click()
                        clicked = True
                        break
                if not clicked:
                    raise RuntimeError("Không tìm thấy nút tạo video. Sửa 'generate_button_texts' trong hailuo_selectors.json.")
                self.log("Đã bấm tạo video, đang chờ kết quả...")
                page.wait_for_function(
                    """([s, before]) => [...document.querySelectorAll(s)].some(
                        e => (e.currentSrc || e.src) && !before.includes(e.currentSrc || e.src))""",
                    arg=[sel["result_video"], list(before)], timeout=sel["wait_result_seconds"] * 1000)
                src = page.eval_on_selector_all(sel["result_video"], "els => els.map(e => e.currentSrc || e.src)")
                new = [s for s in src if s and s not in before][-1]
                data = ctx.request.get(new).body()
                out = out_dir / "video.mp4"
                out.write_bytes(data)
                self.log(f"Đã tải video: {out}")
                return out
            except Exception:
                try:
                    page.screenshot(path=str(out_dir / "loi_hailuo_web.png"))
                    self.log("Đã lưu ảnh chụp màn hình lỗi: loi_hailuo_web.png")
                finally:
                    raise
            finally:
                ctx.close()
