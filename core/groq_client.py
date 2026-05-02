# core/groq_client.py
import os
import time
import json
import hashlib
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from core.config import (
    MODEL_FAST, MAX_RETRIES, RETRY_DELAY, CACHE_DIR, CACHE_TTL_HOURS
)

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
Path(CACHE_DIR).mkdir(exist_ok=True)

print(f"[Groq] Client initialized.")


def build_model(temperature: float = 0.2, use_search: bool = False, smart: bool = False):
    from core.config import MODEL_FAST, MODEL_SMART
    model_name = MODEL_SMART if smart else MODEL_FAST
    if use_search:
        print("[Groq] Note: web search not natively supported, using model knowledge.")
    return {"temperature": temperature, "model_name": model_name}


def _cache_key(model_name: str, prompt: str) -> str:
    return hashlib.sha256(f"{model_name}:{prompt}".encode()).hexdigest()


def _load_cache(key: str):
    path = Path(CACHE_DIR) / f"{key}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    age_hours = (time.time() - data["cached_at"]) / 3600
    if age_hours > CACHE_TTL_HOURS:
        path.unlink()
        return None
    return data["response"]


def _save_cache(key: str, response) -> None:
    path = Path(CACHE_DIR) / f"{key}.json"
    path.write_text(
        json.dumps({"response": response, "cached_at": time.time()}),
        encoding="utf-8"
    )


def stream_groq(model: dict, prompt: str, callback=None) -> str:
    """
    Stream tokens from Groq, calling callback(token) for each chunk.
    Returns the full text. Falls back to call_groq on error.
    Cache-aware: if cached, calls callback with cached text in one shot.
    """
    from core.config import MODEL_FAST
    temperature = model.get("temperature", 0.2) if isinstance(model, dict) else 0.2
    model_name  = model.get("model_name",  MODEL_FAST) if isinstance(model, dict) else MODEL_FAST

    key    = _cache_key(model_name, prompt)
    cached = _load_cache(key)
    if cached is not None and isinstance(cached, str):
        print("[Groq] Cache hit (stream).")
        if callback:
            callback(cached)
        return cached

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise AI assistant. "
                        "When asked for JSON, return ONLY valid JSON — "
                        "no markdown fences, no explanation, no preamble."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=8192,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_text += token
                if callback:
                    callback(token)
    except Exception as e:
        print(f"[Groq] Streaming error: {e}. Falling back to call_groq.")
        return call_groq(model, prompt, expect_json=False)

    if full_text:
        _save_cache(key, full_text)
    return full_text


def call_groq(model: dict, prompt: str, expect_json: bool = True) -> dict | str:
    from core.config import MODEL_FAST, MODEL_SMART

    temperature = model.get("temperature", 0.2) if isinstance(model, dict) else 0.2
    model_name = model.get("model_name", MODEL_FAST) if isinstance(model, dict) else MODEL_FAST

    key = _cache_key(model_name, prompt)
    cached = _load_cache(key)
    if cached is not None:
        print(f"[Groq] Cache hit.")
        return cached

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise AI assistant. "
                            "When asked for JSON, return ONLY valid JSON — "
                            "no markdown fences, no explanation, no preamble."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=2048,
            )

            raw_text = response.choices[0].message.content.strip()

            if not expect_json:
                _save_cache(key, raw_text)
                return raw_text

            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            _save_cache(key, parsed)
            return parsed

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            print(f"[Groq] Attempt {attempt}/{MAX_RETRIES} — {last_error}")

        except Exception as e:
            last_error = str(e)
            err_lower = last_error.lower()
            print(f"[Groq] Attempt {attempt}/{MAX_RETRIES} — {last_error[:120]}")

            if "rate_limit" in err_lower or "429" in last_error:
                # Daily token limit — fall back to fast model immediately
                if "per day" in err_lower or "tpd" in err_lower:
                    if model_name != MODEL_FAST:
                        print(f"[Groq] Daily TPD limit on {model_name}, falling back to {MODEL_FAST}")
                        model_name = MODEL_FAST
                        key = _cache_key(model_name, prompt)
                        cached = _load_cache(key)
                        if cached is not None:
                            return cached
                        continue
                    # Already on fast model and still hitting daily limit
                    break
                # Per-minute / per-request rate limit — wait and retry
                wait = 30 if attempt < MAX_RETRIES else 0
                print(f"[Groq] Rate limited — waiting {wait}s...")
                if wait:
                    time.sleep(wait)
                continue

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    print(f"[Groq] All {MAX_RETRIES} attempts failed.")
    if expect_json:
        return {"error": last_error, "raw": ""}
    return f"[Generation failed: {last_error}]"
