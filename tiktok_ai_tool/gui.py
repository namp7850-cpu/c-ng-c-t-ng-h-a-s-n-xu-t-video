"""Giao diện cửa sổ (Tkinter, nhẹ, hợp máy yếu).  Chạy:  python gui.py
Tab 1: AI viết kịch bản | Tab 2: ảnh + prompt | Tab 3: tạo video (tự động hoặc làm tay)."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import llm
import scriptwriter as sw
from analyzer import HAILUO_MAX_CHARS
from config import Settings
from pipeline import import_video, prepare, render, save, warnings
from providers import PROVIDERS
from providers.minimax_api import PRICE_PER_SEC, estimate_cost


def open_folder(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


class App:
    def __init__(self, root: tk.Tk, cfg: Settings | None = None):
        self.root, self.cfg = root, cfg or Settings()
        self.run = None
        self.q = queue.Queue()
        self.options: list[dict] = []
        root.title("Ảnh → Video AI")
        root.geometry("860x820")
        names = llm.provider_names()
        self.v = {k: tk.StringVar() for k in ("img", "writer", "vision", "analyzer", "provider", "model", "res", "cost", "compare", "status")}
        self.v["writer"].set(self.cfg.writer_provider); self.v["vision"].set(self.cfg.vision_provider)
        self.v["analyzer"].set("none"); self.v["provider"].set("minimax_api")
        self.v["model"].set(self.cfg.minimax_model); self.v["res"].set(self.cfg.minimax_resolution)
        self.v["compare"].set(",".join(names[:3]))
        self.v["status"].set("Bắt đầu: chọn ảnh ở tab 2, hoặc nhờ AI viết kịch bản ở tab 1.")
        self.dur = tk.IntVar(value=6); self.nopt = tk.IntVar(value=3)
        self.names = names

        nb = ttk.Notebook(root); nb.pack(fill="both", expand=True, padx=8, pady=6)
        self.t1, self.t2, self.t3 = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(self.t1, text=" 1. Viết kịch bản (AI) "); nb.add(self.t2, text=" 2. Ảnh + prompt "); nb.add(self.t3, text=" 3. Tạo video ")
        self.nb = nb
        self._tab1(); self._tab2(); self._tab3()
        ttk.Label(root, textvariable=self.v["status"], wraplength=820, foreground="#0a5").pack(anchor="w", padx=10, pady=4)
        self.update_counter(); self.update_cost()
        self._poll()

    # ---------- tiện ích
    def ui(self, fn, *a):
        """Luồng nền chỉ ĐƯA việc vào hàng đợi; luồng chính mới chạm vào giao diện (Tkinter không an toàn đa luồng)."""
        self.q.put((fn, a))

    def _poll(self):
        try:
            while True:
                fn, a = self.q.get_nowait()
                fn(*a)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def status(self, msg):
        self.ui(self.v["status"].set, msg)

    def log(self, msg):
        def w():
            self.logbox.config(state="normal"); self.logbox.insert("end", msg + "\n"); self.logbox.see("end")
            self.logbox.config(state="disabled")
        self.ui(w)

    def snapshot(self) -> dict:
        """Đọc MỌI giá trị giao diện ở luồng chính; luồng nền chỉ dùng bản chụp này."""
        return {"img": self.v["img"].get().strip(), "idea": self.idea.get("1.0", "end").strip(),
                "script": self.script_box.get("1.0", "end").strip(), "edited": self.prompt_box.get("1.0", "end").strip(),
                "analyzer": self.v["analyzer"].get(), "vision": self.v["vision"].get(), "writer": self.v["writer"].get(),
                "compare": [x.strip() for x in self.v["compare"].get().split(",") if x.strip()],
                "n": self.nopt.get(), "dur": self.dur.get(), "prov": self.v["provider"].get()}

    @staticmethod
    def set_text(box, text, ro=False):
        box.config(state="normal"); box.delete("1.0", "end"); box.insert("1.0", text)
        if ro:
            box.config(state="disabled")

    def pick_image(self):
        p = filedialog.askopenfilename(filetypes=[("Ảnh", "*.png *.jpg *.jpeg *.webp")])
        if p:
            self.v["img"].set(p)

    def image_row(self, parent):
        r = ttk.Frame(parent); r.pack(fill="x", padx=6, pady=4)
        ttk.Label(r, text="Ảnh khung đầu:").pack(side="left")
        ttk.Entry(r, textvariable=self.v["img"]).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r, text="Chọn ảnh...", command=self.pick_image).pack(side="left")

    # ---------- Tab 1
    def _tab1(self):
        t = self.t1
        ttk.Label(t, text="Ý tưởng thô của bạn (1-3 câu). AI sẽ biến nó thành kịch bản có hook, logic nhân quả, cú lật.").pack(anchor="w", padx=8, pady=4)
        self.idea = tk.Text(t, height=4, wrap="word"); self.idea.pack(fill="x", padx=8)
        self.image_row(t)
        r = ttk.Frame(t); r.pack(fill="x", padx=8, pady=4)
        ttk.Label(r, text="AI viết:").pack(side="left")
        ttk.Combobox(r, textvariable=self.v["writer"], values=self.names, width=11, state="readonly").pack(side="left", padx=4)
        ttk.Label(r, text="AI nhìn ảnh:").pack(side="left")
        ttk.Combobox(r, textvariable=self.v["vision"], values=self.names, width=11, state="readonly").pack(side="left", padx=4)
        ttk.Label(r, text="Số phương án:").pack(side="left")
        ttk.Spinbox(r, from_=1, to=5, textvariable=self.nopt, width=3).pack(side="left", padx=4)
        self.btn_write = ttk.Button(r, text="Viết kịch bản", command=self.do_write); self.btn_write.pack(side="left", padx=8)
        r2 = ttk.Frame(t); r2.pack(fill="x", padx=8, pady=2)
        ttk.Label(r2, text="So sánh nhiều AI (cách nhau dấu phẩy):").pack(side="left")
        ttk.Entry(r2, textvariable=self.v["compare"], width=34).pack(side="left", padx=4)
        ttk.Button(r2, text="So sánh", command=self.do_compare).pack(side="left")
        self.lb = tk.Listbox(t, height=4, exportselection=False); self.lb.pack(fill="x", padx=8, pady=6)
        self.lb.bind("<<ListboxSelect>>", self.show_option)
        self.detail = tk.Text(t, height=14, wrap="word", state="disabled", background="#f6f6f6"); self.detail.pack(fill="both", expand=True, padx=8)
        ttk.Button(t, text="Dùng phương án này  →  sang tab 2", command=self.use_option).pack(anchor="e", padx=8, pady=6)

    def do_write(self):
        sn = self.snapshot()
        if not sn["idea"]:
            messagebox.showwarning("Thiếu ý tưởng", "Hãy nhập ý tưởng thô."); return
        self.btn_write.config(state="disabled"); self.status("AI đang viết kịch bản...")

        def work():
            try:
                desc = sw.describe(sn["img"], sn["vision"]) if os.path.isfile(sn["img"]) else ""
                data = sw.write_options(sn["idea"], desc, sn["writer"], sn["n"], sn["dur"])
                self.ui(self.fill_options, data, desc)
            except Exception as e:
                self.ui(self.fail, str(e))
        threading.Thread(target=work, daemon=True).start()

    def fill_options(self, data, desc):
        self.options = data.get("options", [])
        self.lb.delete(0, "end")
        for i, o in enumerate(self.options):
            sc = o.get("scores", {})
            star = " ★" if i == data.get("best_index") else ""
            self.lb.insert("end", f"{i + 1}. {o.get('title', '')}{star}   (logic {sc.get('logic', '?')}, hook {sc.get('hook', '?')})")
        self.btn_write.config(state="normal")
        if self.options:
            self.lb.selection_set(data.get("best_index", 0) if isinstance(data.get("best_index"), int) else 0); self.show_option()
        self.status("Đã có phương án. Chọn một cái rồi bấm 'Dùng phương án này'." + (" (đã nhờ AI nhìn ảnh)" if desc else ""))

    def selected(self):
        s = self.lb.curselection()
        return self.options[s[0]] if s and self.options else None

    def show_option(self, _=None):
        o = self.selected()
        if o:
            self.set_text(self.detail, sw.format_option(o), ro=True)

    def use_option(self):
        o = self.selected()
        if not o:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một phương án."); return
        self.set_text(self.script_box, o.get("hailuo_prompt", ""))
        self.nb.select(self.t2); self.status("Đã đưa prompt vào tab 2. Chọn ảnh rồi bấm 'Chuẩn bị'.")

    def do_compare(self):
        sn = self.snapshot()
        if not sn["idea"]:
            messagebox.showwarning("Thiếu ý tưởng", "Hãy nhập ý tưởng thô."); return
        self.status("Đang chạy cùng một đề bài trên " + ", ".join(sn["compare"]) + "...")

        def work():
            try:
                desc = sw.describe(sn["img"], sn["vision"]) if os.path.isfile(sn["img"]) else ""
                p = sw.compare(sn["idea"], desc, sn["compare"], "output/scripts", n=2, duration=sn["dur"])
                self.ui(lambda: (self.status(f"Đã ghi file so sánh: {p}"), open_folder(str(p.parent))))
            except Exception as e:
                self.ui(self.fail, str(e))
        threading.Thread(target=work, daemon=True).start()

    # ---------- Tab 2
    def _tab2(self):
        t = self.t2
        self.image_row(t)
        ttk.Label(t, text="Prompt/kịch bản (tiếng Anh nếu dùng Hailuo; có thể dán từ tab 1):").pack(anchor="w", padx=8)
        self.script_box = tk.Text(t, height=6, wrap="word"); self.script_box.pack(fill="x", padx=8, pady=4)
        r = ttk.Frame(t); r.pack(fill="x", padx=8, pady=4)
        ttk.Label(r, text="Làm gọn/viết lại prompt bằng AI nhìn ảnh:").pack(side="left")
        ttk.Combobox(r, textvariable=self.v["analyzer"], values=["none", "llm"], width=6, state="readonly").pack(side="left", padx=4)
        ttk.Label(r, text="Giây:").pack(side="left")
        ttk.Spinbox(r, from_=4, to=15, textvariable=self.dur, width=4, command=self.update_cost).pack(side="left", padx=4)
        self.btn_prep = ttk.Button(r, text="Chuẩn bị ảnh + prompt", command=self.do_prepare); self.btn_prep.pack(side="left", padx=8)
        ttk.Label(t, text="Mô tả ảnh do AI viết:").pack(anchor="w", padx=8)
        self.desc_box = tk.Text(t, height=3, wrap="word", state="disabled", background="#f2f2f2"); self.desc_box.pack(fill="x", padx=8, pady=2)
        ttk.Label(t, text="Prompt cuối cùng (sửa tự do):").pack(anchor="w", padx=8)
        self.prompt_box = tk.Text(t, height=9, wrap="word"); self.prompt_box.pack(fill="both", expand=True, padx=8, pady=4)
        self.prompt_box.bind("<KeyRelease>", lambda e: self.update_counter())
        self.counter, self.warn = tk.StringVar(), tk.StringVar()
        ttk.Label(t, textvariable=self.counter).pack(anchor="w", padx=8)
        ttk.Label(t, textvariable=self.warn, foreground="#b00020", wraplength=800).pack(anchor="w", padx=8)
        ttk.Button(t, text="Copy prompt", command=self.do_copy).pack(anchor="w", padx=8, pady=6)

    def update_counter(self):
        n = len(self.prompt_box.get("1.0", "end").strip())
        self.counter.set(f"{n}/{HAILUO_MAX_CHARS} ký tự (mức an toàn cho ô nhập web Hailuo; API cho phép dài hơn nhiều)")
        self.warn.set("⚠ Quá dài cho ô nhập web Hailuo, hãy rút gọn." if n > HAILUO_MAX_CHARS else "")

    def ensure_run(self, sn: dict):
        """Chuẩn bị thư mục kết quả + prompt (chạy ở luồng nền, chỉ dùng bản chụp sn)."""
        img, script = sn["img"], sn["script"]
        if not os.path.isfile(img) or not script:
            raise ValueError("Cần chọn ảnh và có prompt/kịch bản ở tab 2.")
        if self.run is None or self.run.image != img or self.run.script != script:
            self.cfg.vision_provider = sn["vision"]
            self.run = prepare(img, script, sn["analyzer"], sn["dur"], "hailuo", "output", self.cfg)
            self.ui(self.set_text, self.desc_box, self.run.description or "(không dùng AI nhìn ảnh)", True)
            self.ui(self.set_text, self.prompt_box, self.run.prompt); self.ui(self.update_counter)
        elif sn["edited"]:
            save(self.run, sn["edited"])
        return self.run

    def do_prepare(self):
        sn = self.snapshot()
        self.run = None
        self.btn_prep.config(state="disabled"); self.status("Đang chuẩn bị...")

        def work():
            try:
                run = self.ensure_run(sn)
                from providers import get_provider
                get_provider("manual", self.cfg, lambda m: None).generate(run.image, run.prompt, run.duration, run.out_dir)
                self.status(f"Đã chuẩn bị. Thư mục kết quả: {run.out_dir}")
            except Exception as e:
                self.ui(self.fail, str(e))
            finally:
                self.ui(self.btn_prep.config, {"state": "normal"})
        threading.Thread(target=work, daemon=True).start()

    def do_copy(self):
        text = self.prompt_box.get("1.0", "end").strip()
        if self.run:
            save(self.run, text)
        self.root.clipboard_clear(); self.root.clipboard_append(text); self.root.update()
        self.status("Đã copy prompt.")

    # ---------- Tab 3
    def _tab3(self):
        t = self.t3
        r = ttk.Frame(t); r.pack(fill="x", padx=8, pady=6)
        ttk.Label(r, text="Cách tạo video:").pack(side="left")
        ttk.Combobox(r, textvariable=self.v["provider"], values=PROVIDERS, width=12, state="readonly").pack(side="left", padx=4)
        ttk.Label(r, text="Model:").pack(side="left")
        models = sorted({m for m, _ in PRICE_PER_SEC})
        cb = ttk.Combobox(r, textvariable=self.v["model"], values=models, width=22, state="readonly"); cb.pack(side="left", padx=4)
        ttk.Label(r, text="Độ phân giải:").pack(side="left")
        cr = ttk.Combobox(r, textvariable=self.v["res"], values=["480P", "768P", "2K"], width=6, state="readonly"); cr.pack(side="left", padx=4)
        for c in (cb, cr):
            c.bind("<<ComboboxSelected>>", lambda e: self.update_cost())
        ttk.Label(t, textvariable=self.v["cost"], foreground="#7a4b00", wraplength=820).pack(anchor="w", padx=8)
        ttk.Label(t, text="• minimax_api: tự động hoàn toàn bằng API chính thức (trả phí theo video).   • hailuo_web: tự động hoá trình duyệt (dùng credit miễn phí, chưa kiểm chứng, xem README).\n"
                  "• manual: làm tay trên web rồi nhập video về.   • kenburns: thử miễn phí, không AI.", wraplength=820, foreground="#555").pack(anchor="w", padx=8, pady=4)
        b = ttk.Frame(t); b.pack(fill="x", padx=8, pady=6)
        self.btn_go = ttk.Button(b, text="▶ Tạo video", command=self.do_generate); self.btn_go.pack(side="left", padx=3)
        ttk.Button(b, text="Mở thư mục kết quả", command=lambda: self.run and open_folder(str(self.run.out_dir))).pack(side="left", padx=3)
        ttk.Button(b, text="Mở Hailuo (làm tay)", command=lambda: webbrowser.open(self.cfg.hailuo_url)).pack(side="left", padx=3)
        ttk.Button(b, text="Nhập video đã tải về", command=self.do_import).pack(side="left", padx=3)
        self.logbox = tk.Text(t, height=18, wrap="word", state="disabled", background="#101010", foreground="#d6ffd6")
        self.logbox.pack(fill="both", expand=True, padx=8, pady=6)

    def update_cost(self, *_):
        self.cfg.minimax_model, self.cfg.minimax_resolution = self.v["model"].get(), self.v["res"].get()
        try:
            c = estimate_cost(self.cfg.minimax_model, self.cfg.minimax_resolution, self.dur.get())
            self.v["cost"].set(f"Ước tính chi phí 1 video {self.dur.get()}s bằng minimax_api: ≈ ${c}  (hạn mức mỗi lần: ${self.cfg.max_usd_per_run}). Giá tra cứu 29/10/2026, hãy kiểm tra lại trên platform.minimax.io.")
        except ValueError as e:
            self.v["cost"].set(f"⚠ {e}")

    def ask_user(self, msg):
        """Cho provider trình duyệt hỏi bạn (chạy trên luồng chính, luồng nền đợi)."""
        ev = threading.Event()
        self.ui(lambda: (messagebox.showinfo("Cần bạn thao tác", msg), ev.set()))
        ev.wait()

    def do_generate(self):
        sn = self.snapshot()
        prov = sn["prov"]
        try:
            if prov == "minimax_api":
                from providers.minimax_api import MiniMaxAPIProvider
                cost = MiniMaxAPIProvider(self.cfg).check(sn["dur"])
                if not messagebox.askyesno("Xác nhận chi phí", f"Việc này sẽ tốn khoảng ${cost} từ số dư MiniMax của bạn. Tiếp tục?"):
                    return
            elif prov == "hailuo_web" and not messagebox.askokcancel(
                    "Lưu ý", "Tự động hoá trình duyệt có thể trái điều khoản của Hailuo và có thể bị hạn chế tài khoản. Công cụ sẽ không vượt xác minh hộ bạn. Tiếp tục?"):
                return
        except Exception as e:
            self.fail(str(e)); return
        self.btn_go.config(state="disabled"); self.status("Đang tạo video, vui lòng chờ (có thể vài phút)...")

        def work():
            try:
                run = self.ensure_run(sn)
                video = render(run, prov, self.cfg, self.log, self.ask_user)
                if video:
                    self.status(f"Xong! Video: {video}")
                    self.ui(lambda: open_folder(str(run.out_dir)))
                else:
                    self.status(f"Đã chuẩn bị ảnh + prompt tại {run.out_dir}. Làm tay trên web rồi bấm 'Nhập video đã tải về'.")
            except Exception as e:
                self.ui(self.fail, str(e))
            finally:
                self.ui(self.btn_go.config, {"state": "normal"})
        threading.Thread(target=work, daemon=True).start()

    def do_import(self):
        if not self.run:
            messagebox.showinfo("Chưa chuẩn bị", "Hãy chuẩn bị hoặc tạo video trước."); return
        p = filedialog.askopenfilename(title="Chọn video đã tải", filetypes=[("Video", "*.mp4 *.mov *.webm")])
        if p:
            self.status(import_video(self.run, p))

    def fail(self, msg):
        self.btn_write.config(state="normal")
        self.status("Lỗi: " + msg[:200])
        self.log("LỖI: " + msg)
        messagebox.showerror("Lỗi", msg)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
