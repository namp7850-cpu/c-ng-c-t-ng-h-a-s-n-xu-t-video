# Ảnh + kịch bản -> video AI 6 giây (tự động hoá quy trình trong video)

Chạy: `python gui.py`  (ba tab: 1. Viết kịch bản bằng AI, 2. Ảnh + prompt, 3. Tạo video)

## Cài đặt trong VS Code
```
python -m venv .venv
.venv\Scripts\activate          (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          (macOS/Linux: cp .env.example .env)
```
Máy yếu vẫn chạy được: không cần torch hay GPU. Cần Python 3.10+ (bản python.org có Tkinter). ffmpeg chỉ cần cho `kenburns` và đọc thông tin video.

## 1) AI viết kịch bản hay hơn
`scriptwriter.py` ép AI viết theo nguyên tắc: hook, chuỗi nhân quả, cú lật được gài mầm, đơn giản để AI video làm được,
khung cuối gợi vòng lặp; tạo nhiều phương án, tự chấm điểm và nêu điểm yếu.
Dùng được MỌI nhà cung cấp có giao diện kiểu OpenAI, khai báo trong `llm_providers.json`
(gemini, groq, openrouter, mistral, github, cerebras). Chỉ cần: điền khoá vào `.env` và điền tên `model`.
- Xem tên model hợp lệ: `python write_script.py --list-models groq`
- Viết: `python write_script.py --idea "cá mập đuổi thuyền" --provider groq --n 3`
- **So sánh AI nào viết hay nhất cho bạn:** `python write_script.py --idea "..." --compare gemini,groq,openrouter`
  (cùng một đề bài, ghi file `.md` để bạn đọc cạnh nhau). Không có nguồn nào xếp hạng độ hay của kịch bản tiếng Việt, nên cách đáng tin là thử.
- Các địa chỉ `base_url` trong `llm_providers.json` là theo hiểu biết của người viết, chưa kiểm chứng hết: nếu lỗi 404, đối chiếu tài liệu nhà cung cấp.
- AI nhìn ảnh cần model hỗ trợ ảnh (đặt `"vision": true`); mặc định chỉ gemini.

## 2) Tạo video tự động
| Cách | Tự động? | Chi phí | Độ tin cậy |
|---|---|---|---|
| `minimax_api` | Hoàn toàn | Trả phí theo video (bảng dưới) | Cao: API chính thức, đã kiểm tra mã theo tài liệu (bằng máy chủ giả lập) |
| `hailuo_web` | Gần hoàn toàn (bạn đăng nhập 1 lần) | Dùng credit miễn phí của tài khoản | Thấp: chưa chạy thử trên trang thật, có thể trái điều khoản |
| `manual` | Không | Miễn phí | Cao |
| `kenburns` | Có | Miễn phí | Chỉ để thử, không dùng AI |
| `wan_local` | Có | Miễn phí | Cần GPU NVIDIA, chưa chạy thử |

### minimax_api (khuyên dùng để tự động thật sự)
1. Tạo tài khoản tại platform.minimax.io, tạo API key, nạp một khoản nhỏ (chọn "Pay-as-you-go API"; H3 chưa dùng được qua gói video trả trước).
2. Điền `MINIMAX_API_KEY` trong `.env`.
3. Giá mỗi giây video đầu ra (tra cứu 29/10/2026, hãy kiểm tra lại): H3-Lite 480P $0.025, H3-Lite 768P $0.04, H3-Highspeed 768P $0.06, H3 768P $0.08, H3 2K $0.13, H3-Max 480P $0.05 / 768P $0.08. Ảnh đầu vào đầu tiên miễn phí.
   Video 6 giây: Lite 480P ≈ $0.15, Lite 768P ≈ $0.24, H3 768P ≈ $0.48.
4. Công cụ hiện chi phí ước tính, hỏi xác nhận trước khi gọi, và chặn nếu vượt `MAX_USD_PER_RUN` (mặc định $0.50).
5. Muốn chất lượng cao hơn: đổi `MINIMAX_MODEL` và `MINIMAX_RESOLUTION` trong `.env` hoặc chọn ngay trên tab 3.

### hailuo_web (tự động hoá trình duyệt, tuỳ chọn, rủi ro)
`pip install playwright` rồi `playwright install chromium`. Công cụ mở một cửa sổ Chromium riêng (hồ sơ lưu ở `.hailuo_profile`, đừng chia sẻ),
bạn tự đăng nhập và xử lý xác minh, mở màn hình Image-to-Video, rồi công cụ tải ảnh, dán prompt, bấm tạo và tải video về.
- Không nhập mật khẩu hộ, không vượt captcha, chỉ làm từng video một.
- Giao diện web đổi thường xuyên: nếu báo không tìm thấy nút/ô, sửa `hailuo_selectors.json`.
- Mình chưa đọc điều khoản dịch vụ của Hailuo về tự động hoá; hãy tự đọc trước khi dùng. Có thể bị hạn chế tài khoản.

## Kết quả
Mỗi lần chạy tạo thư mục `output/<thời gian>/` gồm `video.mp4`, `prompt.txt`, `meta.json`, `input_9x16.png` (và `task.json` nếu dùng API). Xong sẽ tự mở thư mục.

## Dòng lệnh (không cần cửa sổ)
`python main.py --image anh.jpg --script "prompt hoặc file .txt" --provider minimax_api`

## Chưa kiểm chứng (cần bạn thử thật)
- Chất lượng video và độ hay của kịch bản trên mô hình thật.
- Trang web Hailuo thật (`hailuo_web`), nhánh `wan_local` trên GPU, các `base_url` của nhà cung cấp AI ngoài Gemini.
- Hạn mức miễn phí của từng nhà cung cấp AI viết kịch bản thay đổi theo tài khoản.

Dùng ảnh bạn có quyền dùng; kiểm tra chính sách nền tảng trước khi đăng. Không đưa `.env` và `.hailuo_profile` lên GitHub.
