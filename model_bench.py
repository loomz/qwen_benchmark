#!/usr/bin/env python3
"""
Qwen Code Ability & Efficiency Benchmark + reasoning_effort 性能测试

调用路径 (与 Claude Code 相同, 见 model-proxy.py / llama-swap 配置):
  5807 (model-proxy, Anthropic 兼容) -> 8080 (llama-swap) -> 5804 (llama-server)
  - Endpoint: POST /v1/messages  (headers: x-api-key, anthropic-version)
  - 模型: qwen3.8-27b (llama-swap model id: qwen3.8-27b-local)
  - 所有模型有 reasoning (thinking block 在 text block 前流式返回)

用法:
  pip install requests
  python model_bench.py                 # 编码能力全量测试 (默认)
  python model_bench.py --mode effort   # reasoning_effort 性能测试 (3任务×3档×2次)

结果按天存放 -> results/YYYY-MM-DD/benchmark_YYYYMMDD_HHMMSS.{md,json}
              或 results/YYYY-MM-DD/effort_YYYYMMDD_HHMMSS.{md,json}
报告顶部原样记录当前 llama-server 中 qwen3.8 的配置 (进程 cmdline + /props)。
"""

import os
import re
import time
import json
import argparse
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
# qwen3.8 llama-server 配置发现 & reasoning_effort 测试
# 调用路径: 5807 (model-proxy) -> 8080 (llama-swap) -> 5804 (llama-server)
QWEN38_PROC_MATCH = "Qwen3.8-27B-UD-Q4_K_XL.gguf"
QWEN38_LOG_FILE = "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log"

# reasoning_effort 测试: 选 3 个有执行验证的任务, 3 档 effort, 各 2 次
EFFORT_MODEL = ("qwen3.8-27b", "qwen3.8-27b-local")
EFFORT_LEVELS = ["low", "medium", "xhigh"]
EFFORT_TASK_NAMES = ["Fibonacci Memoization", "LRU Cache", "SQL Parser"]
EFFORT_NUM_RUNS = 2
# xhigh 档 thinking 实测可达 ~8000 token (SQL 任务单次推理 4000+ 词), 需足够余量给代码,
# 否则代码被截断/未产出 (模型到 EOS 会停, 不会真生成到上限; 16384 覆盖 thinking+代码)
EFFORT_MAX_TOKENS = 16384

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
    # reasoning_effort 测试专用
    effort: str = ""
    rendered_effort: str = ""
    effort_confirmed: bool = False
    effort_detail: str = ""


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


# ---------------------------------------------------------------------------
# qwen3.8 llama-server 配置发现 (报告顶部原样记录当前配置)
# ---------------------------------------------------------------------------
def discover_qwen38() -> dict:
    """定位运行中的 qwen3.8 llama-server 进程, 返回 {pid, cmdline, port}。
    pgrep 可能返回多个 PID (含已退出的), 只取仍存活且 cmdline 含 llama-server 的。"""
    try:
        out = subprocess.run(
            ["pgrep", "-f", QWEN38_PROC_MATCH],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception as e:
        return {"error": f"pgrep failed: {e}"}
    for pid in [p for p in out.split() if p.strip()]:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                raw = f.read()
        except OSError:
            continue  # 进程已退出
        cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
        if "llama-server" not in cmdline:
            continue
        port = None
        toks = cmdline.split()
        for i, t in enumerate(toks):
            if t == "--port" and i + 1 < len(toks):
                port = toks[i + 1]
                break
        return {"pid": pid, "cmdline": cmdline, "port": port}
    return {"error": f"no live llama-server matched {QWEN38_PROC_MATCH}"}


def read_qwen38_config() -> dict:
    """读取 qwen3.8 llama-server 当前配置: 进程 cmdline (原样) + /props (运行时)。"""
    disc = discover_qwen38()
    cfg = {
        "cmdline": disc.get("cmdline", ""),
        "port": disc.get("port"),
        "pid": disc.get("pid"),
        "props": None,
        "error": disc.get("error", ""),
    }
    if cfg["port"]:
        try:
            r = requests.get(f"http://127.0.0.1:{cfg['port']}/props", timeout=10)
            r.raise_for_status()
            cfg["props"] = r.json()
        except Exception as e:
            cfg["error"] = f"cmdline OK, /props failed: {e}"
    return cfg


def config_header_md(cfg: dict) -> str:
    """报告顶部: 原样记录当前 llama-server 中 qwen3.8 的配置。"""
    L = []
    L.append("## 0. 当前 llama-server 配置 (qwen3.8-27b, 原样记录)")
    L.append("")
    if cfg.get("error"):
        L.append(f"> ⚠️ 配置读取: {cfg['error']}")
        L.append("")
    if cfg.get("cmdline"):
        L.append(f"**进程** (PID {cfg.get('pid')}, port {cfg.get('port')}):")
        L.append("")
        L.append("```bash")
        L.append(cfg["cmdline"])
        L.append("```")
        L.append("")
    if cfg.get("props") is not None:
        L.append("**/props (运行时状态, 原样):**")
        L.append("")
        L.append("```json")
        L.append(json.dumps(cfg["props"], ensure_ascii=False, indent=2))
        L.append("```")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# reasoning_effort 日志渲染校验 (best-effort, 异步 flush)
# ---------------------------------------------------------------------------
def verify_effort_batch(items, log_file: str = QWEN38_LOG_FILE,
                        max_wait: int = 45, poll: int = 2) -> None:
    """批量从 llama-server --log-file 校验每个请求实际渲染的 reasoning_effort。

    items: [(marker, requested_effort, size_before, Result)]。
    日志由单线程 worker 异步 flush (launch_slot 行含完整渲染 prompt), 最后一个
    请求的行可能延迟 >20s, 故从最小 size_before 起增量读 (只读新字节, 保留跨行
    残尾), 有界轮询。medium 档模板不注入指令, 渲染=none 为预期。
    """
    expected = {"low": "low", "xhigh": "xhigh", "medium": "none"}
    pending = {m: (eff, tr) for (m, eff, _sb, tr) in items}
    if not pending:
        return
    try:
        offset = min(sb for (_m, _e, sb, _t) in items)
    except ValueError:
        offset = 0
    tail = ""
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline and pending:
        try:
            size = os.path.getsize(log_file)
        except OSError:
            time.sleep(poll)
            continue
        if size > offset:
            try:
                with open(log_file, "rb") as f:
                    f.seek(offset)
                    chunk = f.read(size - offset).decode("utf-8", "replace")
                offset = size
            except OSError:
                time.sleep(poll)
                continue
            buf = tail + chunk
            nl = buf.rfind("\n")
            if nl == -1:  # 整段是未写完的超长行, 等下一轮
                tail = buf
                continue
            tail = buf[nl + 1:]
            for line in buf.splitlines():
                if "launch_slot" not in line:
                    continue
                for m in list(pending):
                    if m in line:
                        m2 = re.search(r"Reasoning effort is set to (\w+)", line)
                        rendered = m2.group(1) if m2 else "none"
                        eff, tr = pending[m]
                        tr.rendered_effort = rendered
                        tr.effort_confirmed = (rendered == expected.get(eff))
                        tr.effort_detail = f"log: rendered={rendered} (requested={eff})"
                        del pending[m]
        if pending:
            time.sleep(poll)
    for m, (eff, tr) in pending.items():
        tr.rendered_effort = "not_flushed"
        tr.effort_confirmed = False
        tr.effort_detail = f"log: not flushed within {max_wait}s (requested={eff})"


def call_model(model_id: str, prompt: str, effort: str = None,
               marker: str = None, max_tokens: int = None) -> dict:
    # Anthropic Messages API (same protocol Claude Code speaks)
    payload = {
        "model": model_id,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        **GEN_KWARGS,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if effort is not None:
        payload["output_config"] = {"effort": effort}
    if marker is not None:
        # marker 只进 HTTP body (不进 bash 命令行), 故只出现在本请求的 launch_slot 日志行
        payload["messages"][0]["content"] = f"[bench-marker: {marker}]\n\n{prompt}"
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
    print(f"  Qwen Code Benchmark  {now}")
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


def run_effort_bench() -> tuple:
    """reasoning_effort 性能测试: 3 任务 × 3 档 effort × 2 次。

    每个请求带唯一 marker (嵌入 HTTP body, 不进 bash 命令行), 结束后批量从日志
    校验渲染出的 effort 指令; 同时用行为信号 (推理 token/耗时) 作为主确认。
    """
    dn, mid = EFFORT_MODEL
    tasks = [t for t in TASKS if t["name"] in EFFORT_TASK_NAMES]
    cfg = read_qwen38_config()  # 记录测试开始时的配置
    results: List[Result] = []
    log_items = []  # (marker, requested_effort, size_before, Result)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 70)
    print(f"  Qwen3.8 reasoning_effort Benchmark  {now}")
    print(f"  Server: {API_URL}  ->  llama-server :{cfg.get('port')}")
    print(f"  Model: {dn}  |  Tasks: {[t['name'] for t in tasks]}")
    print(f"  Effort levels: {EFFORT_LEVELS}  |  Runs: {EFFORT_NUM_RUNS}")
    print("=" * 70)

    for task in tasks:
        for effort in EFFORT_LEVELS:
            for idx in range(EFFORT_NUM_RUNS):
                marker = (f"EB_{task['name'].replace(' ', '_')}"
                          f"_{effort}_{int(time.time() * 1000)}")
                try:
                    size_before = os.path.getsize(QWEN38_LOG_FILE)
                except OSError:
                    size_before = 0
                print(f"  {task['name']:<24} {effort:<7} #{idx + 1} ... ",
                      end="", flush=True)
                try:
                    info = call_model(mid, task["prompt"], effort=effort,
                                      marker=marker, max_tokens=EFFORT_MAX_TOKENS)
                    tr = Result(
                        task=task["name"], diff=task["diff"], model=dn, run=idx,
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
                        effort=effort,
                    )
                    if task["verify"]:
                        if (info["content_text"] or "").strip():
                            code = extract_code(info["content_text"])
                            passed, detail = verify_code(code)
                            tr.code_pass = passed
                            tr.code_detail = detail
                        else:
                            # xhigh 推理耗尽 token 预算, 未产出代码 (不拿 thinking 当代码执行)
                            tr.code_pass = False
                            tr.code_detail = "no code: thinking exhausted budget"
                    results.append(tr)
                    log_items.append((marker, effort, size_before, tr))
                    think_s = max(0.0, info["ttft_content_s"] - info["ttft_reasoning_s"])
                    tag = "PASS" if tr.code_pass else ("FAIL" if task["verify"] else "SKIP")
                    print(
                        f"think={info['reasoning_tokens']}w/{think_s:.1f}s  "
                        f"total={info['total_s']:.2f}s  "
                        f"{info['predict_tps']:.1f}tok/s  [{tag}]"
                    )
                except Exception as e:
                    print(f"ERROR: {e}")
                    results.append(Result(
                        task=task["name"], diff=task["diff"], model=dn, run=idx,
                        verify=task["verify"], effort=effort, error=str(e),
                    ))

    print(f"\n  校验日志中的 reasoning_effort 渲染 (等待异步 flush, 最多 45s)...",
          flush=True)
    verify_effort_batch(log_items)
    return results, cfg


def gen_report(results: List[Result], cfg: dict) -> str:
    models_label = ", ".join(dn for dn, _ in MODELS)
    L = []
    L.append(f"# Qwen 编码能力 & 效率基准测试 ({models_label})")
    L.append("")
    L.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"硬件: RTX 5090D 24G")
    L.append(f"服务端: model-proxy @ {API_URL} -> llama-swap :8080 -> llama-server :{cfg.get('port')}")
    L.append(f"每任务运行: {NUM_RUNS} 次")
    L.append("")
    L.append(config_header_md(cfg))
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


def gen_effort_report(results: List[Result], cfg: dict) -> str:
    L = []
    L.append("# Qwen3.8 reasoning_effort 性能基准测试")
    L.append("")
    L.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"服务端: {API_URL} -> llama-swap :8080 -> llama-server :{cfg.get('port')}")
    L.append(f"模型: {EFFORT_MODEL[0]}  |  任务: {', '.join(EFFORT_TASK_NAMES)}  |  每档运行 {EFFORT_NUM_RUNS} 次")
    L.append("")
    L.append("> 指标: 推理Tok=thinking 词数, 推理耗时≈TTFT代码-TTFT推理, 总Tok 来自 API usage (精确)。")
    L.append("> 切换确认: 主信号=行为 (各档推理量差异); 辅证=日志渲染出的 effort 指令 (best-effort, 异步 flush)。")
    L.append("")

    # Part 3: 配置原样记录
    L.append(config_header_md(cfg))

    # §1 明细表
    L.append("## 1. 明细")
    L.append("")
    L.append("| 任务 | effort | # | 推理Tok | 推理耗时(s) | 总耗时(s) | 总Tok | 生成Tok/s | 切换确认 | 渲染effort | 通过 |")
    L.append("|------|--------|---|---------|-------------|-----------|-------|-----------|----------|------------|------|")
    for r in results:
        if r.error:
            L.append(f"| {r.task} | {r.effort} | {r.run + 1} | - | - | - | - | - | ERROR | - | - |")
            continue
        think_s = max(0.0, r.ttft_content_s - r.ttft_reasoning_s)
        conf = "✅" if r.effort_confirmed else ("⚠️" if r.rendered_effort else "—")
        ps = "Y" if r.code_pass else ("N" if r.verify else "-")
        L.append(
            f"| {r.task} | {r.effort} | {r.run + 1}"
            f" | {r.reasoning_tokens}"
            f" | {think_s:.2f}"
            f" | {r.total_s:.2f}"
            f" | {r.total_tokens}"
            f" | {r.predict_tps:.1f}"
            f" | {conf}"
            f" | {r.rendered_effort or '-'}"
            f" | {ps} |"
        )
    L.append("")

    # §2 任务×effort 均值
    L.append("## 2. 任务 × effort 均值")
    L.append("")
    L.append("| 任务 | effort | 推理Tok | 推理耗时(s) | 总耗时(s) | 生成Tok/s | 通过率 |")
    L.append("|------|--------|---------|-------------|-----------|-----------|--------|")
    for task in EFFORT_TASK_NAMES:
        for effort in EFFORT_LEVELS:
            mr = [r for r in results if r.task == task and r.effort == effort and not r.error]
            if not mr:
                continue
            think_s = [max(0.0, r.ttft_content_s - r.ttft_reasoning_s) for r in mr]
            passed = sum(1 for r in mr if r.code_pass)
            L.append(
                f"| {task} | {effort}"
                f" | {statistics.mean(r.reasoning_tokens for r in mr):.0f}"
                f" | {statistics.mean(think_s):.2f}"
                f" | {statistics.mean(r.total_s for r in mr):.2f}"
                f" | {statistics.mean(r.predict_tps for r in mr):.1f}"
                f" | {passed}/{len(mr)} |"
            )
    L.append("")

    # §3 切换确认
    L.append("## 3. reasoning_effort 切换确认")
    L.append("")
    L.append("### 3a. 行为信号 (主确认)")
    L.append("")
    L.append("各 effort 档的平均推理量 (thinking 词数 / 推理耗时)。若 xhigh 显著高于 low, 说明 effort 指令确实改变了模型推理深度。")
    L.append("")
    L.append("| effort | 平均推理Tok | 平均推理耗时(s) | 平均总耗时(s) |")
    L.append("|--------|-------------|-----------------|---------------|")
    for effort in EFFORT_LEVELS:
        mr = [r for r in results if r.effort == effort and not r.error]
        if not mr:
            continue
        think_s = [max(0.0, r.ttft_content_s - r.ttft_reasoning_s) for r in mr]
        L.append(
            f"| {effort}"
            f" | {statistics.mean(r.reasoning_tokens for r in mr):.0f}"
            f" | {statistics.mean(think_s):.2f}"
            f" | {statistics.mean(r.total_s for r in mr):.2f} |"
        )
    L.append("")

    L.append("### 3b. 日志渲染确认 (辅证, best-effort)")
    L.append("")
    L.append("从 llama-server `--log-file` 的 `launch_slot` 行提取每个请求实际渲染的 effort 指令。")
    L.append("medium 档模板不注入指令 (渲染=none 为预期)。日志异步缓冲 flush, 个别请求可能未 flush 到。")
    L.append("")
    L.append("| 任务 | effort | 请求 | 渲染effort | 匹配 | 说明 |")
    L.append("|------|--------|------|------------|------|------|")
    for r in results:
        if r.error or not r.effort:
            continue
        match = "✅" if r.effort_confirmed else "❌"
        L.append(f"| {r.task} | {r.effort} | #{r.run + 1} | {r.rendered_effort or '-'} | {match} | {r.effort_detail} |")
    L.append("")

    # 结论
    def _avg(effort: str, attr: str) -> float:
        mr = [r for r in results if r.effort == effort and not r.error]
        return statistics.mean(getattr(r, attr) for r in mr) if mr else 0.0
    low_r = _avg("low", "reasoning_tokens")
    xhigh_r = _avg("xhigh", "reasoning_tokens")
    n_log = sum(1 for r in results if r.effort and r.effort_confirmed)
    n_tot = sum(1 for r in results if r.effort and not r.error)
    L.append("### 3c. 结论")
    L.append("")
    if low_r and xhigh_r and xhigh_r > low_r:
        L.append(f"- **行为确认**: xhigh 平均推理 {xhigh_r:.0f} 词 > low 平均 {low_r:.0f} 词, "
                 f"effort 切换**生效**。")
    else:
        L.append(f"- **行为**: xhigh 推理 {xhigh_r:.0f} 词 vs low {low_r:.0f} 词 "
                 f"(未观察到显著差异, 需人工复核)。")
    L.append(f"- **日志确认**: {n_log}/{n_tot} 个请求的渲染 effort 与请求值一致。")
    L.append("")

    # §4 代码样例: 每任务挑一个有代码的 xhigh run; 若该任务 xhigh 全部未产出代码, 说明原因
    L.append("## 4. 代码输出样例 (每任务 xhigh)")
    L.append("")
    xhigh_by_task = {}
    for r in results:
        if r.error or r.effort != "xhigh":
            continue
        xhigh_by_task.setdefault(r.task, []).append(r)
    for task in [t["name"] for t in TASKS if t["name"] in EFFORT_TASK_NAMES]:
        runs = xhigh_by_task.get(task)
        if not runs:
            continue
        pick = next((r for r in runs if (r.content_text or "").strip()), None)
        L.append(f"### {task} (xhigh)")
        if pick is not None:
            if pick.code_pass:
                L.append("**执行: PASS**")
            elif pick.code_detail:
                L.append(f"**执行: {pick.code_detail}**")
            L.append("")
            L.append("```python")
            L.append(pick.content_text[:2000])
            L.append("```")
        else:
            tw = max(r.reasoning_tokens for r in runs)
            L.append(
                f"> ⚠️ xhigh 各次运行均在推理阶段耗尽 {EFFORT_MAX_TOKENS} token 预算, "
                f"未产出代码 (单次推理达 {tw} 词)。"
            )
        L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Qwen benchmark")
    ap.add_argument("--mode", choices=["ability", "effort"], default="ability",
                    help="ability=编码能力全量测试; effort=reasoning_effort 性能测试")
    args = ap.parse_args()

    # 结果按天存放: results/YYYY-MM-DD/<prefix>_<ts>.{md,json}
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / now.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "effort":
        results, cfg = run_effort_bench()
        txt = gen_effort_report(results, cfg)
        prefix = "effort"
    else:
        cfg = read_qwen38_config()
        results = run_bench()
        txt = gen_report(results, cfg)
        prefix = "benchmark"

    md = out_dir / f"{prefix}_{ts}.md"
    md.write_text(txt, encoding="utf-8")

    jp = out_dir / f"{prefix}_{ts}.json"
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
            "effort": r.effort,
            "rendered_effort": r.rendered_effort,
            "effort_confirmed": r.effort_confirmed,
            "effort_detail": r.effort_detail,
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
