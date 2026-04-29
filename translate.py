import json
import os
import re
import sys

import requests

_DEFAULTS = {
    "ollama_url": "http://localhost:11434/api/generate",
    "model": "qwen3.5:9b",
}


def _load_config() -> dict:
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "config.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_DEFAULTS, f, indent=2)
        return dict(_DEFAULTS)
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return {**_DEFAULTS, **cfg}


_cfg = _load_config()
OLLAMA_URL: str = _cfg["ollama_url"]
MODEL: str = _cfg["model"]


def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    if not text.strip():
        return ""

    prompt = (
        f"Translate the following {src_lang} text to {tgt_lang}. "
        f"Output only the translated text, no explanation.\n\n{text}"
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "think": False},
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        # Qwen3 thinking 태그 제거
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        return raw.strip()
    except requests.exceptions.ConnectionError:
        return "[Ollama 연결 실패 — localhost:11434 확인]"
    except Exception as e:
        return f"[번역 오류: {e}]"
