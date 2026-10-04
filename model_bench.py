#!/usr/bin/env python3
"""
Qwen3.6 & Qwen3.8 Code Ability & Efficiency Benchmark
Tests qwen3.6-27b vs qwen3.8-27b vs qwen3.8-35b-a3b on code generation.

Your setup (same as Claude Code, from ~/.claude/settings.json):
  - Server: llama-swap @ http://localhost:8080 (Anthropic-compatible API)
  - Endpoint: POST /v1/messages  (headers: x-api-key, anthropic-version)
  - Models: qwen3.6-27b, qwen3.8-27b, qwen3.6-35b (llama-swap model ids)
  - All models have reasoning (thinking block streamed before text block)

Usage:
  pip install requests
  python model_bench.py

Results -> results/benchmark_YYYYMMDD_HHMMSS.{md,json}
"""

import time
import json
import textwrap
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List

import requests

# ---------------------------------------------------------------------------
# Same endpoint & protocol as Claude Code (ANTHROPIC_BASE_URL in settings.json)
API_URL = "http://localhost:5807/v1/messages"
API_KEY = "local"
ANTHROPIC_VERSION = "2023-06-01"

MODELS = [
    ("qwen3.8-27b",       "qwen3.8-27b-local"),
    # ("qwen3.6-27b",       "qwen3.6-27b"),
    # ("qwen3.6-35b",   "qwen3.6-35b"),
]

GEN_KWARGS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "max_tokens": 4096,
}

NUM_RUNS = 3
OUTPUT_DIR = Path(__file__).parent / "results"

# ---------------------------------------------------------------------------
TASKS = [
    {
        "name": "Fibonacci Memoization",
        "diff": "easy",
        "prompt": textwrap.dedent("""\
            完成以下 Python 函数，用装饰器实现记忆化，支持任意深度递归。
            写完后写 3 个 assert 测试，包含边界 (n=0, n=1, n=20)。

            ```python
            from functools import wraps

            def memoize(func):
            ```

            ```python
            def fibonacci(n):
            ```

            只输出代码。
        """),
        "verify": True,
    },
    {
        "name": "LRU Cache",
        "diff": "medium",
        "prompt": textwrap.dedent("""\
            用 Python 实现 LRU Cache：
            1. get(key), put(key, value)，时间复杂度 O(1)
            2. 线程安全 (threading.Lock)
            3. 完整类型注解
            4. 包含 3 个测试用例

            只输出代码。
        """),
        "verify": True,
    },
    {
        "name": "Async Task Queue",
        "diff": "hard",
        "prompt": textwrap.dedent("""\
            实现异步任务队列：
            1. 优先级调度 (heapq)
            2. 失败重试指数退避最多 3 次
            3. 可配置并发数
            4. 统计完成/失败/重试次数
            5. 可运行示例

            只输出代码。
        """),
        "verify": False,
    },
    {
        "name": "SQL Parser",
        "diff": "hard",
        "prompt": textwrap.dedent("""\
            实现简单 SQL 解析器，解析 SELECT col FROM table WHERE cond。
            返回 dict: {selected_columns, table_name, where_conditions}。
            使用正则，不依赖第三方库，包含测试。

            只输出代码。
        """),
        "verify": True,
    },
    {
        "name": "HTTP Downloader",
        "diff": "hard",
        "prompt": textwrap.dedent("""\
            实现并发 HTTP 下载器：
            1. URL 列表并发下载
            2. asyncio.Semaphore 限流
            3. 超时重试
            4. 返回 {url, status, size, elapsed_ms}

            只输出代码。
        """),
        "verify": False,
    },
]

SYSTEM = (
    "你是一个资深 Python 工程师。直接输出可运行代码，"
    "用 ```python 包裹，不要其他文字。"
)


@dataclass
class Result:
    task: str
    diff: str
    model: str
    run: int
    content_text: str = ""
    reasoning_text: str = ""
    ttft_reasoning_s: float = 0.0
    ttft_content_s: float = 0.0
    total_s: float = 0.0
    reasoning_tokens: int = 0
    content_tokens: int = 0
    total_tokens: int = 0
    prompt_tps: float = 0.0
    predict_tps: float = 0.0
    verify: bool = False
    code_pass: bool = False
    code_detail: str = ""
    error: str = ""


def extract_code(text: str) -> str:
    s = text.find("```python")
    if s != -1:
        s += len("```python")
        e = text.rfind("```", s)
        if e != -1:
            return text[s:e].strip()
    s = text.find("```")
    if s != -1:
        e = text.rfind("```", s + 3)
        if e != -1:
            return text[s + 3:e].strip()
    return text


def verify_code(code: str) -> tuple:
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            out = (r.stdout or r.stderr).strip()[:200]
            return True, out or "OK"
        return False, r.stderr.strip()[:200] or "non-zero exit"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:200]


def call_model(model_id: str, prompt: str) -> dict:
    # Anthropic Messages API (same protocol Claude Code speaks)
    payload = {
        "model": model_id,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        **GEN_KWARGS,
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
    }

    # llama-swap may 502 while swapping models; retry once after a pause
    resp = None
    for attempt in range(2):
        resp = requests.post(API_URL, json=payload, headers=headers,
                             timeout=600, stream=True)
        if resp.status_code == 502:
            if attempt == 0:
                print(" (swap, waiting 60s...)  ", flush=True)
                time.sleep(60)
            else:
                resp.raise_for_status()
        else:
            resp.raise_for_status()
            break

    full_content = ""
    full_reasoning = ""
    first_reasoning_ts = None
    first_content_ts = None
    t_start = time.monotonic()
    input_tokens = 0
    output_tokens = 0

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8")
        if not line.startswith("data: "):
            continue
        ds = line[6:]
        if ds.strip() == "[DONE]":
            break
        try:
            data = json.loads(ds)
        except json.JSONDecodeError:
            continue

        etype = data.get("type", "")
        if etype == "message_start":
            input_tokens = (data.get("message", {})
                            .get("usage", {}).get("input_tokens", 0))
        elif etype == "content_block_delta":
            delta = data.get("delta", {})
            dtype = delta.get("type", "")
            if dtype == "thinking_delta":
                if first_reasoning_ts is None:
                    first_reasoning_ts = time.monotonic()
                full_reasoning += delta.get("thinking", "")
            elif dtype == "text_delta":
                if first_content_ts is None:
                    first_content_ts = time.monotonic()
                full_content += delta.get("text", "")
        elif etype == "message_delta":
            output_tokens = data.get("usage", {}).get("output_tokens", 0)
        elif etype == "message_stop":
            break

    total_s = time.monotonic() - t_start
    ttft_r = (first_reasoning_ts - t_start) if first_reasoning_ts else 0
    ttft_c = (first_content_ts - t_start) if first_content_ts else total_s

    # Anthropic API exposes no server timings; estimate from the stream:
    #   predict_tps = output tokens / (first-token -> end)
    #   prompt_tps  = input tokens  / (start -> first token)  (upper bound)
    gen_span = total_s - ttft_r
    predict_tps = output_tokens / gen_span if gen_span > 0 else 0.0
    prompt_tps = input_tokens / ttft_r if ttft_r > 0 else 0.0

    return {
        "content_text": full_content,
        "reasoning_text": full_reasoning,
        "ttft_reasoning_s": round(ttft_r, 4),
        "ttft_content_s": round(ttft_c, 4),
        "total_s": round(total_s, 4),
        "reasoning_tokens": len(full_reasoning.split()),
        "content_tokens": len(full_content.split()),
        "total_tokens": output_tokens,
        "prompt_tps": round(prompt_tps, 1),
        "predict_tps": round(predict_tps, 1),
    }


def run_bench() -> List[Result]:
    results: List[Result] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print(f"  Qwen3.6 Code Benchmark  {now}")
    print(f"  Server: {API_URL}")
    print(f"  Models: {len(MODELS)}  |  Tasks: {len(TASKS)}  |  Runs: {NUM_RUNS}")
    print("=" * 70)

    for task in TASKS:
        print(f"\n{'-' * 60}")
        print(f"  [{task['diff'].upper()}] {task['name']}")
        print(f"{'-' * 60}")

        for dn, mid in MODELS:
            for idx in range(NUM_RUNS):
                print(f"  {dn} #{idx + 1} ...", end=" ", flush=True)

                try:
                    info = call_model(mid, task["prompt"])

                    tr = Result(
                        task=task["name"],
                        diff=task["diff"],
                        model=dn,
                        run=idx,
                        verify=task["verify"],
                        content_text=info["content_text"][:3000],
                        reasoning_text=info["reasoning_text"][:1000],
                        ttft_reasoning_s=info["ttft_reasoning_s"],
                        ttft_content_s=info["ttft_content_s"],
                        total_s=info["total_s"],
                        reasoning_tokens=info["reasoning_tokens"],
                        content_tokens=info["content_tokens"],
                        total_tokens=info["total_tokens"],
                        prompt_tps=info["prompt_tps"],
                        predict_tps=info["predict_tps"],
                    )

                    if task["verify"]:
                        code = extract_code(info["content_text"] or info["reasoning_text"])
                        passed, detail = verify_code(code)
                        tr.code_pass = passed
                        tr.code_detail = detail

                    results.append(tr)
                    tag = "PASS" if tr.code_pass else ("FAIL" if task["verify"] else "SKIP")
                    print(
                        f"{info['predict_tps']:.1f} tok/s  "
                        f"TTFT_r={info['ttft_reasoning_s']:.2f}s  "
                        f"TTFT_c={info['ttft_content_s']:.2f}s  "
                        f"total={info['total_s']:.2f}s  "
                        f"[{tag}]"
                    )

                except Exception as e:
                    print(f"ERROR: {e}")
                    results.append(
                        Result(
                            task=task["name"],
                            diff=task["diff"],
                            model=dn,
                            run=idx,
                            content_text="",
                            reasoning_text="",
                            error=str(e),
                        )
                    )

    return results


def gen_report(results: List[Result]) -> str:
    L = []
    L.append("# Qwen3.6 编码能力 & 效率基准测试")
    L.append("")
    L.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"硬件: RTX 5090D 24G")
    L.append(f"服务端: llama-swap @ localhost:8080 (Anthropic API, 与 Claude Code 相同)")
    L.append(f"每任务运行: {NUM_RUNS} 次")
    L.append("")
    L.append("> \\* 速度为客户端估算: 生成速度=输出Tok/首Tok后耗时, Prompt速度=输入Tok/首Tok延迟; 总Tok 来自 API usage (精确)。")
    L.append("")

    for dn, mid in MODELS:
        mr = [r for r in results if r.model == dn and not r.error]
        if not mr:
            L.append(f"## {dn} -- 无数据")
            L.append("")
            continue

        L.append(f"## {dn}")
        L.append("")
        L.append(
            "| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) "
            "| 推理Tok | 代码Tok | 总Tok | 生成Tok/s* | 通过 |"
        )
        L.append(
            "|------|---|-------------|-------------|----------"
            "|---------|---------|-------|-------------|------|"
        )
        for r in mr:
            detail = r.code_detail[:16] if r.code_detail else ""
            ps = "Y" if r.code_pass else f"N({detail})" if r.verify else "-"
            L.append(
                f"| {r.task} | {r.run + 1}"
                f" | {r.ttft_reasoning_s:.2f}"
                f" | {r.ttft_content_s:.2f}"
                f" | {r.total_s:.2f}"
                f" | {r.reasoning_tokens}"
                f" | {r.content_tokens}"
                f" | {r.total_tokens}"
                f" | {r.predict_tps:.1f}"
                f" | {ps} |"
            )

        # Averages
        ttft_rs = [r.ttft_reasoning_s for r in mr]
        ttft_cs = [r.ttft_content_s for r in mr]
        totals = [r.total_s for r in mr]
        r_toks = [r.reasoning_tokens for r in mr]
        c_toks = [r.content_tokens for r in mr]
        tpss = [r.predict_tps for r in mr]
        p_tps = [r.prompt_tps for r in mr]
        passed = sum(1 for r in mr if r.code_pass)

        L.append("")
        L.append(
            f"**均值**: TTFT推理={statistics.mean(ttft_rs):.2f}s, "
            f"TTFT代码={statistics.mean(ttft_cs):.2f}s, "
            f"总耗时={statistics.mean(totals):.2f}s, "
            f"推理Tok={statistics.mean(r_toks):.0f}, "
            f"代码Tok={statistics.mean(c_toks):.0f}, "
            f"服务端Tok/s={statistics.mean(tpss):.1f}, "
            f"PromptTok/s={statistics.mean(p_tps):.1f}, "
            f"通过率={passed}/{len(mr)}"
        )
        L.append("")

    # Comparison
    L.append("## 对比总结")
    L.append("")

    model_names = [dn for dn, _ in MODELS]
    header = "| 指标 | " + " | ".join(model_names) + " |"
    sep = "|------|" + "|".join(["-------" for _ in model_names]) + "|"
    L.append(header)
    L.append(sep)

    for key, label in [
        ("ttft_r", "首字延迟-推理 (s)"),
        ("ttft_c", "首字延迟-代码 (s)"),
        ("total", "总耗时 (s)"),
        ("tps", "生成速度 (tok/s)*"),
        ("ptps", "Prompt 速度 (tok/s)*"),
        ("r_tok", "推理 Token 数"),
        ("c_tok", "代码 Token 数"),
        ("pass", "代码通过率"),
    ]:
        vals = []
        for dn2, mid2 in MODELS:
            mr2 = [r for r in results if r.model == dn2 and not r.error]
            if not mr2:
                vals.append("N/A")
                continue
            if key == "ttft_r":
                vals.append(f"{statistics.mean(r.ttft_reasoning_s for r in mr2):.2f}")
            elif key == "ttft_c":
                vals.append(f"{statistics.mean(r.ttft_content_s for r in mr2):.2f}")
            elif key == "total":
                vals.append(f"{statistics.mean(r.total_s for r in mr2):.2f}")
            elif key == "tps":
                vals.append(f"{statistics.mean(r.predict_tps for r in mr2):.1f}")
            elif key == "ptps":
                vals.append(f"{statistics.mean(r.prompt_tps for r in mr2):.1f}")
            elif key == "r_tok":
                vals.append(f"{statistics.mean(r.reasoning_tokens for r in mr2):.0f}")
            elif key == "c_tok":
                vals.append(f"{statistics.mean(r.content_tokens for r in mr2):.0f}")
            elif key == "pass":
                p = sum(1 for r in mr2 if r.code_pass) / len(mr2)
                vals.append(f"{p:.0%}")
        L.append(f"| {label} | " + " | ".join(vals) + " |")

    L.append("")
    L.append("## 代码输出样例")
    L.append("")
    seen = set()
    for r in results:
        k = (r.model, r.task)
        if k in seen or r.error:
            continue
        seen.add(k)
        L.append(f"### {r.model} - {r.task}")
        if r.code_pass:
            L.append("**执行: PASS**")
        elif r.code_detail:
            L.append(f"**执行: {r.code_detail}**")
        L.append("")
        L.append("```python")
        L.append(r.content_text[:2000])
        L.append("```")
        L.append("")

    return "\n".join(L)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = run_bench()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt = gen_report(results)
    md = OUTPUT_DIR / f"benchmark_{ts}.md"
    md.write_text(txt, encoding="utf-8")

    jp = OUTPUT_DIR / f"benchmark_{ts}.json"
    jd = []
    for r in results:
        jd.append({
            "task": r.task,
            "difficulty": r.diff,
            "model": r.model,
            "run": r.run,
            "ttft_reasoning_s": r.ttft_reasoning_s,
            "ttft_content_s": r.ttft_content_s,
            "total_s": r.total_s,
            "reasoning_tokens": r.reasoning_tokens,
            "content_tokens": r.content_tokens,
            "total_tokens": r.total_tokens,
            "prompt_tps": r.prompt_tps,
            "predict_tps": r.predict_tps,
            "code_pass": r.code_pass,
            "code_detail": r.code_detail,
            "error": r.error,
            "content_preview": r.content_text[:500],
            "reasoning_preview": r.reasoning_text[:500],
        })
    jp.write_text(
        json.dumps(jd, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"\n{'=' * 70}")
    print(f"  Report: {md}")
    print(f"  JSON:   {jp}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
