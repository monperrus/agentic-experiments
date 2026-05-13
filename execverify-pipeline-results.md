# ExecVerify Pipeline Run — Results Report

**Source repo:** https://github.com/tlx000000001/ExecVerify  
**Run date:** 2026-05-13  
**Environment:** Ubuntu / Python 3.12, CPU-only (no GPU available)

---

## What Is ExecVerify?

ExecVerify is a research pipeline for training LLMs to reason about code execution (execution reasoning) and generate correct code, using **white-box reinforcement learning** driven by interpreter traces.

The pipeline has three main phases:

1. **Constraint-based Data Synthesis** — generates Python code with structural constraints, synthesises diverse inputs, filters by executability and difficulty, and extracts interpreter execution traces to form RL rewards.
2. **Two-Stage Post-Training** — Stage I applies white-box RL (interpreter-trace-derived step-level rewards); Stage II transfers to code generation using unit-test rewards.
3. **Evaluation** — benchmarks on CRUXEval, LiveCodeBench-Exec, REval, EvalPlus, LiveCodeBench, BigCodeBench, and CRUXEval-X.

---

## What Was Actually Run

The full ExecVerify pipeline requires NVIDIA GPUs and ~200 GB of disk for model checkpoints (Qwen2.5-Coder-7B for SFT, QwQ-32B for code/reasoning synthesis). Since no GPU is available, the following was executed:

| Pipeline Step | Status | Notes |
|---|---|---|
| **Step 1** – Code Synthesis (`code_synthesis.py`) | ❌ Skipped | Requires vLLM + 32 B LLM |
| **Step 2** – Input Synthesis (`input_synthesis.py`) | ❌ Skipped | Requires vLLM |
| **Step 3** – Filter by Execution (`filter_by_execution.py`) | ✅ **Ran** | CPU-only; ran on synthetic sample |
| **Step 4** – Filter by Difficulty (`filter_by_difficulty.py`) | ❌ Skipped | Requires vLLM |
| **Step 5** – Combine Data | ❌ Skipped | No intermediate files |
| **Steps 6–8** – CoT / SFT / RL Candidate Extraction | ❌ Skipped | Requires vLLM |
| **Step 9** – Extract Execution Traces (`extract_trace.py`) | ✅ **Ran** | CPU-only; ran on synthetic sample |
| **Step 10** – Build RL Trace Dataset | ❌ Skipped | No intermediate files |
| **SFT Training** (LLaMA-Factory) | ❌ Skipped | Requires 8× A100-class GPUs |
| **RL Stage I** (verl / GRPO) | ❌ Skipped | Requires cluster of GPUs |
| **RL Stage II** (unit-test RL) | ❌ Skipped | Requires cluster of GPUs |
| **Evaluation** (CRUXEval, LiveCodeBench, …) | ❌ Skipped | Requires vLLM + GPU |
| **Public HuggingFace dataset analysis** | ✅ **Ran** | Both released datasets downloaded and analysed |

---

## Step 3 — Filter by Execution: Results

A synthetic mini-dataset of 20 samples (mimicking `raw_dataset.json` output from Step 1) was fed into the `filter_by_execution.py` logic.

| Metric | Value |
|---|---|
| Input samples | 20 |
| Passed filter | 17 |
| Filtered out | 3 |
| Pass rate | **85 %** |

**Filter rejection reasons:**
- 1 × execution error (`ZeroDivisionError`)
- 1 × execution timeout (deep recursion, `n = 100 000`)
- 1 × no `print(func(...))` wrapper pattern (uses intermediate variable)

**Sample passing results:**

```
test_str_upper("hello")                         == 'HELLO'
test_list_append([1, 2, 3], 4)                  == [1, 2, 3, 4]
test_dict_get({"a": 1, "b": 2}, "a")            == 1
test_str_split("hello world foo", " ")          == ['hello', 'world', 'foo']
test_set_add([1, 2, 3], 4)                      == [1, 2, 3, 4]
entry([3, 1, 2], 0)                             == [0, 1, 2, 3]   # call-chain sample
test_str_join(["hello", "world"], " ")          == 'hello world'
test_str_replace("hello world", "world","Python")== 'hello Python'
test_list_sort([3, 1, 4, 1, 5])                 == True
test_set_difference([1, 2, 3, 4], [2, 4])       == [1, 3]
test_dict_keys({"c": 3, "a": 1, "b": 2})        == ['a', 'b', 'c']
test_str_lower("HELLO WORLD")                   == 'hello world'
... (5 more)
```

---

## Step 9 — Execution Trace Extraction: Results

Interpreter traces (`sys.settrace`) were extracted for all 17 passing samples.

| Metric | Value |
|---|---|
| Samples with traces | 17 / 17 |
| Avg trace length | 6.4 events |
| Min trace length | 4 events |
| Max trace length | 15 events |

**Example trace** for `test_str_split("hello world foo", " ")` (15 events):
```
[call] line 1  locals: [s, sep]
[line] line 2  locals: [s, sep]
[line] line 3  locals: [s, sep, parts]
[line] line 4  locals: [s, sep, parts, result]
[line] line 5  locals: [s, sep, parts, result]
[line] line 6  locals: [s, sep, parts, result]  ← for-loop body (×3 iterations)
[line] line 7  locals: [s, sep, parts, result]
... (8 more events)
[return] line 8
```

These trace events become the foundation of the **step-level RL reward signal** used in Stage I training.

---

## Dataset Analysis (Public HuggingFace Releases)

### SFT Dataset (`justForAnonymous/sft_dataset`)

| Property | Value |
|---|---|
| Total samples | **30,000** |
| Format | 2-turn conversation (human + assistant) |
| Task split | 15,000 IO (predict output given input) + 15,000 OI (predict input given output) |
| Avg reasoning chain length | **~812 words** per sample |

**Task format (IO — predict output):**
```
Try to execute the program step by step and fill in the missing assertion.
Try to find out the ???? in the following code.
...
assert test_str_concat(test_str_concat("hello", " "), test_str_concat("world", "!")) == ????
```

**Task format (OI — predict input):**
```
...
assert test_str_concat(????) == 'hello world!'
```

Each assistant response contains a `<reasoning>…</reasoning>` block with step-by-step mental simulation before the final answer.

### RL Dataset (`justForAnonymous/rl_dataset`)

| Property | Value |
|---|---|
| Total samples | **32,000** |
| Type: `io_mixed` | 20,000 (62.5 %) |
| Type: `oi` | 12,000 (37.5 %) |
| Unique function templates | 339 |
| Avg function length | 11.8 lines |
| Avg arguments per function | 3.0 |
| Avg trace events per sample | 17.3 events |
| Avg path-flow questions | 2.9 per sample |
| Avg state-variable questions | 1.9 per sample |

**Trace event distribution:**

| Trace length | Samples | Share |
|---|---|---|
| < 10 events | 9,913 | 31 % |
| 10–20 events | 4,006 | 12.5 % |
| > 20 events | 6,081 | 19 % |

**Question types in RL dataset:**

Each RL sample has two kinds of verifiable questions generated from the interpreter trace:

- **Path-flow questions** ("which line executes immediately after line X at iteration N?") — avg 2.9 per sample
- **State-variable questions** ("is line X executed? if so, what is the value of variable Y after the Nth execution?") — avg 1.9 per sample

Example path-flow question:
> *"While executing `test_str_multiply("abc", 3)`, which line of code is executed immediately after line 6: `if processed.pop() == s[0]:` has been executed for the 3rd time?"*

---

## Published Evaluation Results (from ExecVerify paper)

Since model inference requires GPUs, the published benchmark numbers are reproduced here from the ExecVerify repository and paper.

### Execution Reasoning Benchmarks

| Model | CRUXEval-I | CRUXEval-O | LCB-Exec | Avg |
|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct (base) | — | — | — | 60.8 |
| **ExecVerify Stage I** (white-box RL) | — | — | — | **80.8** |
| Qwen2.5-Coder-32B-Instruct | — | — | — | 77.9 |

**Key finding:** Stage I improves average execution-reasoning score by **+20.0 points** (60.8 → 80.8), competitive with the 32B model while using only a 7B base.

### Code Generation Benchmarks

| Model | HumanEval+ | MBPP+ | Notes |
|---|---|---|---|
| Stage II (unit-test RL) | best of class | best of class | +5.9 pass@1 over strong baselines |

---

## Infrastructure Requirements (Not Met in This Environment)

To run the **full** pipeline end-to-end, the following would be needed:

| Component | Requirement |
|---|---|
| Code/reasoning synthesis (Steps 1, 2) | 1–4× A100 80 GB GPUs; QwQ-32B model (~65 GB) |
| Difficulty filtering (Step 4) | GPU; Qwen2.5-Coder-7B |
| SFT training | 8× A100 80 GB; ~2 days |
| RL Stage I training | 8–16× A100; GRPO via verl framework |
| RL Stage II training | 8–16× A100 |
| CRUXEval/LCB evaluation | 1× A100; vLLM |
| Disk space (models + datasets) | ~300 GB |

---

## Summary

The ExecVerify pipeline is a sophisticated research infrastructure combining:
- **Automated dataset construction** (CPU-feasible steps demonstrated above)
- **Interpreter-trace-driven RL rewards** (novel contribution; Step 9 demonstrated)
- **Two-stage LLM post-training** (requires multi-GPU cluster)
- **Multi-benchmark evaluation** (requires GPU inference)

The CPU-feasible portions of the pipeline ran correctly. The filter-by-execution step achieved an 85% pass rate on synthetic samples, and all 17 passing samples produced valid interpreter traces suitable for RL reward construction.

The published results show that ExecVerify's white-box RL approach delivers a **+20-point improvement** in execution reasoning and **+5.9 pass@1** in code generation over strong SFT baselines.
