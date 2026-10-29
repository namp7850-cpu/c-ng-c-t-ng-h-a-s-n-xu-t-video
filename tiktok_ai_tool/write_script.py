"""Viết kịch bản bằng AI (dòng lệnh).
  python write_script.py --idea "..." --provider groq --n 3
  python write_script.py --idea "..." --image anh.jpg --vision-provider gemini --provider openrouter
  python write_script.py --idea "..." --compare gemini,groq,openrouter      (so sánh nhiều AI)
  python write_script.py --list-models groq                               (xem tên model để điền vào llm_providers.json)
"""
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
import llm
import scriptwriter as sw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idea")
    ap.add_argument("--image")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--vision-provider", default="gemini")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--duration", type=int, default=6)
    ap.add_argument("--compare", help="danh sách nhà cung cấp, ngăn cách bằng dấu phẩy")
    ap.add_argument("--list-models")
    ap.add_argument("--out", default="output/scripts")
    a = ap.parse_args()

    if a.list_models:
        print("\n".join(llm.list_models(a.list_models)))
        return
    if not a.idea:
        ap.error("cần --idea (hoặc --list-models)")
    desc = sw.describe(a.image, a.vision_provider) if a.image else ""
    if desc:
        print("Mô tả ảnh:", desc, "\n")
    if a.compare:
        p = sw.compare(a.idea, desc, [x.strip() for x in a.compare.split(",")], a.out, n=max(1, a.n - 1), duration=a.duration)
        print("Đã ghi file so sánh:", p)
        return
    data = sw.write_options(a.idea, desc, a.provider, a.n, a.duration)
    for i, o in enumerate(data["options"]):
        print(f"\n===== PHƯƠNG ÁN {i + 1}{'  (AI chọn)' if i == data.get('best_index') else ''} =====")
        print(sw.format_option(o))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    f = Path(a.out) / "ket_qua_gan_nhat.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nĐã lưu:", f)


if __name__ == "__main__":
    main()
