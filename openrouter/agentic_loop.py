#!/usr/bin/env python3
"""
Small agentic loop via OpenRouter Responses API with google/gemma-4-31b-it:free.

Tests whether the model can:
  1. Choose to call a tool
  2. Use the tool result to produce a final answer

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python agentic_loop.py
"""

import os
import json
import math
import requests

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/responses"
MODEL = "google/gemma-4-31b-it:free"
MAX_TURNS = 5

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ── Tools ────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "name": "calculator",
        "description": "Evaluate a mathematical expression and return the numeric result.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python-evaluable math expression, e.g. '2 ** 10' or 'math.sqrt(144)'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "type": "function",
        "name": "reverse_string",
        "description": "Reverse a string and return it.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The string to reverse"}
            },
            "required": ["text"],
        },
    },
]


def run_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments)
    if name == "calculator":
        try:
            result = eval(args["expression"], {"__builtins__": {}}, {"math": math})
            return str(result)
        except Exception as e:
            return f"error: {e}"
    if name == "reverse_string":
        return args["text"][::-1]
    return f"unknown tool: {name}"


# ── Responses API call ────────────────────────────────────────────────────────

def call_api(input_items: list) -> dict:
    payload = {
        "model": MODEL,
        "input": input_items,
        "tools": TOOLS,
        "tool_choice": "auto",
    }
    resp = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Agentic loop ──────────────────────────────────────────────────────────────

def extract_text(output: list) -> str | None:
    for item in output:
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part["text"]
    return None


def run(user_question: str) -> str:
    print(f"\nUser: {user_question}")
    history = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": user_question}],
        }
    ]

    for turn in range(MAX_TURNS):
        body = call_api(history)
        output = body.get("output", [])

        # Collect tool calls in this turn
        tool_calls = [item for item in output if item.get("type") == "function_call"]

        if not tool_calls:
            # Model is done — extract final text
            text = extract_text(output)
            if text:
                print(f"Assistant: {text}")
                return text
            print(f"Assistant (raw output): {json.dumps(output, indent=2)}")
            return str(output)

        # Execute each tool call and append results to history
        for tc in tool_calls:
            result = run_tool(tc["name"], tc["arguments"])
            print(f"  [tool] {tc['name']}({tc['arguments']}) → {result}")
            history.append(tc)  # the function_call item
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": tc["call_id"],
                    "output": result,
                }
            )

    return "max turns reached"


# ── Test cases ────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("ERROR: set OPENROUTER_API_KEY environment variable")
        return

    print(f"Model: {MODEL}")
    print("=" * 60)

    questions = [
        "What is 2 ** 10 + math.sqrt(144)?",
        "Reverse the string 'Hello, agentic world!' and tell me what you get.",
        "What is the square root of 1764 divided by 3?",
    ]

    for q in questions:
        run(q)
        print()


if __name__ == "__main__":
    main()
