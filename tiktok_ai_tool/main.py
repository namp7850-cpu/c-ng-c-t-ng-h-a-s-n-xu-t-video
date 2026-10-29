"""Dòng lệnh. Ảnh + kịch bản -> (AI phân tích) -> video ngắn.

Ví dụ:
  python main.py --image anh.jpg --script examples/script.txt --provider manual
  python main.py --image anh.jpg --script "..." --analyzer llm --provider minimax_api
Muốn dùng cửa sổ: python gui.py
"""
import argparse
from pathlib import Path

from config import Settings
from pipeline import prepare, render, warnings
from providers import PROVIDERS


def read_script(value: str) -> str:
    try:
        p = Path(value)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    except OSError:  # chuỗi quá dài hoặc chứa ký tự không hợp lệ cho tên tệp -> coi là văn bản
        pass
    return value


def main():
    ap = argparse.ArgumentParser(description="Ảnh + kịch bản -> video AI ngắn")
    ap.add_argument("--image", required=True)
    ap.add_argument("--script", required=True, help="chuỗi văn bản hoặc đường dẫn file .txt")
    ap.add_argument("--analyzer", choices=["none", "llm"], default="none")
    ap.add_argument("--provider", choices=PROVIDERS, default="manual")
    ap.add_argument("--target", choices=["generic", "hailuo"], default="hailuo",
                    help="định dạng prompt: hailuo = tối ưu cho ô nhập của Hailuo")
    ap.add_argument("--vision-provider", help="AI nhìn ảnh (tên trong llm_providers.json)")
    ap.add_argument("--duration", type=int, default=6)
    ap.add_argument("--out", default="output")
    a = ap.parse_args()

    cfg = Settings()
    if a.vision_provider:
        cfg.vision_provider = a.vision_provider
    print("[1/3] Phân tích ảnh và ghép prompt...")
    run = prepare(a.image, read_script(a.script), a.analyzer, a.duration, a.target, a.out, cfg)
    print("      Mô tả ảnh:", run.description or "(bỏ qua)")
    print("      Prompt:", run.prompt)
    for w in warnings(run):
        print("      CẢNH BÁO:", w)
    print(f"[2/3] Provider '{a.provider}'...")
    video = render(run, a.provider, cfg)
    print(f"[3/3] Xong. Thư mục kết quả: {run.out_dir}")
    if video:
        print("      Video:", video)


if __name__ == "__main__":
    main()
