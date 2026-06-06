#!/usr/bin/env python3
"""
Try the OpenRouter Responses API with free models to find which supports it best.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python responses_api.py
"""

import os
import json
import requests
import time

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/responses"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Free models on OpenRouter (as of June 2026)
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-coder:free",
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k2.6:free",
    "openrouter/free",
]

PROMPT = "What is 2+2? Answer in one sentence."


def try_model(model: str) -> dict:
    payload = {"model": model, "input": PROMPT}
    start = time.time()
    try:
        resp = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=30)
        elapsed = time.time() - start
        return {
            "model": model,
            "status": resp.status_code,
            "elapsed_s": round(elapsed, 2),
            "ok": resp.status_code == 200,
            "body": resp.json(),
        }
    except Exception as e:
        return {
            "model": model,
            "status": None,
            "elapsed_s": round(time.time() - start, 2),
            "ok": False,
            "body": {"error": str(e)},
        }


def extract_text(body: dict) -> str:
    """Pull the assistant text out of a Responses API reply."""
    # Responses API shape: {"output": [{"content": [{"text": "..."}]}]}
    try:
        for item in body.get("output", []):
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part["text"]
        # Fallback: look for any 'text' key in output
        return json.dumps(body.get("output", body))[:200]
    except Exception:
        return str(body)[:200]


def main():
    if not API_KEY:
        print("ERROR: set OPENROUTER_API_KEY environment variable")
        return

    print(f"Testing OpenRouter Responses API ({BASE_URL})")
    print(f"Prompt: {PROMPT!r}\n")

    results = []
    for model in FREE_MODELS:
        print(f"  → {model} ...", end=" ", flush=True)
        result = try_model(model)
        results.append(result)
        status_tag = "OK" if result["ok"] else f"FAIL({result['status']})"
        print(f"{status_tag} ({result['elapsed_s']}s)")
        if result["ok"]:
            print(f"     {extract_text(result['body'])!r}")
        else:
            err = result["body"].get("error", result["body"])
            print(f"     error: {err}")
        print()
        time.sleep(0.5)  # gentle rate-limit courtesy

    # Summary
    working = [r for r in results if r["ok"]]
    print(f"\n--- Summary ---")
    print(f"Working models: {len(working)}/{len(results)}")
    if working:
        fastest = min(working, key=lambda r: r["elapsed_s"])
        print(f"Fastest: {fastest['model']} ({fastest['elapsed_s']}s)")
        print("\nAll working models:")
        for r in working:
            print(f"  {r['model']}  ({r['elapsed_s']}s)")


if __name__ == "__main__":
    main()
