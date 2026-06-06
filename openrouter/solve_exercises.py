#!/usr/bin/env python3
"""
Generate solutions for the first N exercises from ASSERT-KTH/exercise-10k
using google/gemma-4-31b-it:free via the OpenRouter Responses API.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python solve_exercises.py --exercises-dir /tmp/exercise-10k/exercises --n 10
"""

import os
import json
import glob
import argparse
import requests
import re
from datetime import datetime, timezone

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/responses"
MODEL = "google/gemma-4-31b-it:free"
MODEL_SLUG = MODEL.replace("/", "-").replace(":", "-")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def extract_prompt(md_path: str) -> str | None:
    """Pull the exercise description out of an exercise_NNNNN.md file."""
    with open(md_path) as f:
        content = f.read()
    m = re.search(r"## Exercise\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if not m:
        return None
    return m.group(1).strip()


def call_responses_api(prompt: str) -> str | None:
    payload = {"model": MODEL, "input": prompt}
    try:
        resp = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        for item in body.get("output", []):
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part["text"]
        return None
    except Exception as e:
        print(f"    API error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercises-dir", default="/tmp/exercise-10k/exercises")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: set OPENROUTER_API_KEY environment variable")
        return

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(__file__), "answers", MODEL_SLUG
    )
    os.makedirs(output_dir, exist_ok=True)

    exercise_files = sorted(glob.glob(os.path.join(args.exercises_dir, "exercise_*.md")))
    exercise_files = exercise_files[: args.n]

    print(f"Model : {MODEL}")
    print(f"Output: {output_dir}")
    print(f"Solving {len(exercise_files)} exercises\n")

    for path in exercise_files:
        exercise_id = re.search(r"exercise_(\d+)\.md", path).group(1)
        out_path = os.path.join(output_dir, f"{exercise_id}.json")

        if os.path.exists(out_path):
            print(f"[{exercise_id}] already solved, skipping")
            continue

        prompt = extract_prompt(path)
        if not prompt:
            print(f"[{exercise_id}] could not extract prompt, skipping")
            continue

        print(f"[{exercise_id}] {prompt[:80]}...")
        answer = call_responses_api(prompt)

        if answer:
            result = {
                "prompt": prompt,
                "answer": answer,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": MODEL,
            }
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"         saved ({len(answer)} chars)\n")
        else:
            print(f"         no answer returned\n")

    print("Done.")


if __name__ == "__main__":
    main()
