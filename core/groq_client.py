# core/gemini_client.py — Groq version
import os
import time
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 4
RETRY_DELAY = 5
MODEL_FAST = "llama-3.1-8b-instant"    # Classifier, Visualizer, simple tasks
MODEL_SMART = "llama-3.3-70b-versatile"  # Analyst, Devil, Synthesizer, Writer

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
print(f"[Groq] Client initialized. Models: fast={MODEL_FAST}, smart={MODEL_SMART}")


def build_model(temperature: float = 0.2, use_search: bool = False, smart: bool = False):
    model_name = MODEL_SMART if smart else MODEL_FAST
    if use_search:
        print("[Groq] Note: web search not available, using model knowledge.")
    return {
        "temperature": temperature,
        "use_search": use_search,
        "model_name": model_name
    }


def call_gemini(model: dict, prompt: str, expect_json: bool = True) -> dict | str:
    temperature = model.get("temperature", 0.2) if isinstance(model, dict) else 0.2
    model_name = model.get("model_name", MODEL_FAST) if isinstance(model, dict) else MODEL_FAST
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
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=4096,
            )

            raw_text = response.choices[0].message.content.strip()

            if not expect_json:
                return raw_text

            # Strip markdown fences if model adds them anyway
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            return json.loads(raw_text)

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            print(f"[Groq] Attempt {attempt}/{MAX_RETRIES} — {last_error}")

        except Exception as e:
            last_error = str(e)
            print(f"[Groq] Attempt {attempt}/{MAX_RETRIES} — {last_error[:120]}")

            # Handle Groq rate limit (very rare but possible)
            if "rate_limit" in last_error.lower() or "429" in last_error:
                print(f"[Groq] Rate limited — waiting 30s...")
                time.sleep(30)
                continue

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    print(f"[Groq] All {MAX_RETRIES} attempts failed.")
    if expect_json:
        return {"error": last_error, "raw": ""}
    else:
        return f"[Generation failed: {last_error}]"