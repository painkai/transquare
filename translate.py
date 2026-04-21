import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"


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
