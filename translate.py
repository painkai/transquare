import json
import os
import re
import sys

import requests

_DEFAULTS = {
    "ollama_url": "http://localhost:11434/api/generate",
    "model": "qwen2.5:14b-instruct-q4_K_M",
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


def _call_ollama(text: str, src_lang: str, tgt_lang: str) -> str:
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


_JA_LANGS = {"japanese", "일본어", "ja", "jpn"}
_KO_LANGS = {"korean", "한국어", "ko", "kor"}


def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    if not text.strip():
        return ""

    # 일본어 → 한국어: 일본어를 먼저 영어로 번역한 뒤 영어를 한국어로 번역
    if src_lang.lower() in _JA_LANGS and tgt_lang.lower() in _KO_LANGS:
        english = _call_ollama(text, src_lang, "English")
        if english.startswith("["):
            return english
        return _call_ollama(english, "English", tgt_lang)

    return _call_ollama(text, src_lang, tgt_lang)
