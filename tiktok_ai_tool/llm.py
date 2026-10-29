"""Gọi mọi mô hình ngôn ngữ có giao diện kiểu OpenAI (chat/completions) bằng một đoạn mã duy nhất.
Đổi nhà cung cấp = sửa llm_providers.json, không phải sửa mã."""
import base64
import io
import json
import os
import re
from pathlib import Path

import requests
from PIL import Image

CONFIG_FILE = Path(__file__).with_name("llm_providers.json")


def load_providers() -> dict:
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def provider_names() -> list[str]:
    return list(load_providers())


def _get(name: str, need_model=True):
    provs = load_providers()
    if name not in provs:
        raise ValueError(f"Không có nhà cung cấp '{name}'. Có: {', '.join(provs)}")
    p = provs[name]
    key = os.getenv(p["api_key_env"], "")
    if not key:
        raise RuntimeError(f"Thiếu {p['api_key_env']} trong file .env (khoá API của '{name}').")
    if need_model and not p.get("model"):
        raise RuntimeError(f"Chưa điền 'model' cho '{name}' trong llm_providers.json. "
                           f"Xem danh sách: python write_script.py --list-models {name}")
    return p, key


def _headers(p, key):
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    h.update(p.get("extra_headers", {}))
    return h


def image_data_uri(path: str, max_side: int = 1024) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def chat(name, messages, image_path=None, json_mode=False, temperature=0.9, max_tokens=2000, timeout=120) -> str:
    p, key = _get(name)
    if image_path:
        if not p.get("vision"):
            raise RuntimeError(f"'{name}' chưa được đánh dấu hỗ trợ ảnh (vision) trong llm_providers.json.")
        last = messages[-1]
        messages = messages[:-1] + [{"role": last["role"], "content": [
            {"type": "text", "text": last["content"]},
            {"type": "image_url", "image_url": {"url": image_data_uri(image_path)}}]}]
    payload = {"model": p["model"], "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode and p.get("json_mode", True):
        payload["response_format"] = {"type": "json_object"}
    r = requests.post(p["base_url"].rstrip("/") + "/chat/completions", headers=_headers(p, key),
                      json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"{name}: lỗi HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"] or ""


def list_models(name: str) -> list[str]:
    p, key = _get(name, need_model=False)
    r = requests.get(p["base_url"].rstrip("/") + "/models", headers=_headers(p, key), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{name}: lỗi HTTP {r.status_code}: {r.text[:300]}")
    return sorted(m.get("id", "") for m in r.json().get("data", []))


def extract_json(text: str) -> dict:
    """Lấy đối tượng JSON từ câu trả lời của AI (kể cả khi bọc trong ```json ... ```)."""
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("AI không trả về JSON")
    return json.loads(t[s:e + 1])
