#!/usr/bin/env python3
"""
Qwen Code Ability & Efficiency Benchmark + reasoning_effort 性能测试

调用路径 (统一走 llama-swap, 见 llama-swap config.yaml):
  8080 (llama-swap, OpenAI 兼容) -> llama-server (动态端口)
  - Endpoint: POST /v1/chat/completions  (headers: Authorization: Bearer none)
  - 模型: 见 bench_config.py (ACTIVE profile, openai_model 即 llama-swap key)
  - thinking 模型流式先返回 reasoning_content (思考), 再返回 content (代码)

用法:
  pip install requests
  python model_bench.py                 # 编码能力全量测试 (默认 effort=medium, --effort 覆盖)
  python model_bench.py --effort xhigh # 指定 ability 模式的 reasoning_effort
  python model_bench.py --mode effort   # reasoning_effort 性能测试 (3任务×3档×2次)

结果按天存放 -> results/YYYY-MM-DD/benchmark_YYYYMMDD_HHMMSS.{md,json}
              或 results/YYYY-MM-DD/effort_YYYYMMDD_HHMMSS.{md,json}
报告顶部原样记录当前 llama-server 中该 profile 的配置 (进程 cmdline + /props)。
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

# 模型相关配置集中在 bench_config.py (切换模型改那里的 ACTIVE, 支持多个 profile)
from bench_config import active_profiles, get_profile, PAUSE_SECONDS
# 模型服务 (llama-server; ninfer profile 为 ninfer-serve) 配置发现/记录, 与 evalplus_bench 共享
from bench_utils import read_qwen38_config, config_header_md

# ---------------------------------------------------------------------------
# 统一走 llama-swap (8080, OpenAI 兼容 /v1/chat/completions); model-proxy 5807 已停用
API_URL = "http://localhost:8080/v1/chat/completions"
API_KEY = "none"

# 待测模型: 由 bench_config.ACTIVE profile 决定 (每个 profile 一个模型, 见 bench_config.py)

GEN_KWARGS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "max_tokens": 4096,
}

NUM_RUNS = 3
OUTPUT_DIR = Path(__file__).parent / "results"

# 能力 benchmark 默认 reasoning_effort 与 token 上限 (可用 --effort / --max-tokens 覆盖)
# 默认 medium; 需更高推理深度时显式 --effort xhigh (xhigh thinking 可达数千 token,
# max_tokens 需留足余量给代码, 否则硬任务代码被截断)
BENCH_EFFORT = "medium"
BENCH_MAX_TOKENS = 16384

# ---------------------------------------------------------------------------
# qwen3.8 llama-server 配置发现 & reasoning_effort 测试
# 调用路径: 8080 (llama-swap) -> llama-server (动态端口)
# 模型相关 (proc_match / openai_model / log_file / display_name) 由 bench_config.py 的
# ACTIVE profile 提供, 运行时按 profile 传入各函数 (见 main)。

# reasoning_effort 测试: 选 3 个有执行验证的任务, 3 档 effort, 各 2 次
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


# 模型服务 (llama-server; ninfer profile 为 ninfer-serve) 配置发现/唤醒/记录
# 在 bench_utils.read_qwen38_config (与 evalplus_bench.py 共享)




# ---------------------------------------------------------------------------
# reasoning_effort 日志渲染校验 (best-effort, 异步 flush)
# ---------------------------------------------------------------------------
def verify_effort_batch(items, log_file: str,
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
    # OpenAI Chat Completions (llama-swap 8080, 统一路径; model-proxy 已停用)
    user_content = prompt
    if marker is not None:
        # marker 只进 HTTP body (不进 bash 命令行), 故只出现在本请求的 launch_slot 日志行
        user_content = f"[bench-marker: {marker}]\n\n{prompt}"
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        **GEN_KWARGS,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if effort is not None:
        # llama-server 原生支持请求级 effort (output_config/reasoning/reasoning_effort 三种格式)
        payload["reasoning_effort"] = effort
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
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

        # OpenAI 流式: chunk 可带 usage (stream_options.include_usage) 与 choices[0].delta
        usage = data.get("usage")
        if usage:
            input_tokens = usage.get("prompt_tokens", input_tokens)
            output_tokens = usage.get("completion_tokens", output_tokens)

        choices = data.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        # thinking 模型: 先 reasoning_content (思考), 后 content (代码); 无思考时前者缺失
        rc = delta.get("reasoning_content")
        if rc:
            if first_reasoning_ts is None:
                first_reasoning_ts = time.monotonic()
            full_reasoning += rc
        c = delta.get("content")
        if c:
            if first_content_ts is None:
                first_content_ts = time.monotonic()
            full_content += c

    total_s = time.monotonic() - t_start
    ttft_r = (first_reasoning_ts - t_start) if first_reasoning_ts else 0
    ttft_c = (first_content_ts - t_start) if first_content_ts else total_s

    # OpenAI API 不直接给服务端计时; 从流估算:
    #   predict_tps = 输出 token / (首 token -> 结束)
    #   prompt_tps  = 输入 token / (开始 -> 首 token)  (上界)
    gen_span = total_s - ttft_r
    predict_tps = output_tokens / gen_span if gen_span > 0 else 0.0
    prompt_tps = input_tokens / ttft_r if ttft_r > 0 else 0.0

    # total_tokens 优先取 usage.completion_tokens (精确); 缺失时回退按词估算
    if not output_tokens:
        output_tokens = len(full_reasoning.split()) + len(full_content.split())

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


def run_bench(profile: dict, effort: str = BENCH_EFFORT,
              max_tokens: int = BENCH_MAX_TOKENS) -> List[Result]:
    models = [(profile["display_name"], profile["openai_model"])]
    results: List[Result] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print(f"  Qwen Code Benchmark  {now}  (profile={profile['name']})")
    print(f"  Server: {API_URL}")
    print(f"  Models: {len(models)}  |  Tasks: {len(TASKS)}  |  Runs: {NUM_RUNS}")
    print(f"  reasoning_effort: {effort}  |  max_tokens: {max_tokens}")
    print("=" * 70)

    for task in TASKS:
        print(f"\n{'-' * 60}")
        print(f"  [{task['diff'].upper()}] {task['name']}")
        print(f"{'-' * 60}")

        for dn, mid in models:
            for idx in range(NUM_RUNS):
                print(f"  {dn} #{idx + 1} ...", end=" ", flush=True)

                try:
                    info = call_model(mid, task["prompt"], effort=effort,
                                      max_tokens=max_tokens)

                    tr = Result(
                        task=task["name"],
                        diff=task["diff"],
                        model=dn,
                        run=idx,
                        verify=task["verify"],
                        effort=effort,
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


def run_effort_bench(profile: dict) -> tuple:
    """reasoning_effort 性能测试: 3 任务 × 3 档 effort × 2 次。

    每个请求带唯一 marker (嵌入 HTTP body, 不进 bash 命令行), 结束后批量从日志
    校验渲染出的 effort 指令; 同时用行为信号 (推理 token/耗时) 作为主确认。
    """
    dn, mid = profile["display_name"], profile["openai_model"]
    tasks = [t for t in TASKS if t["name"] in EFFORT_TASK_NAMES]
    cfg = read_qwen38_config(profile)  # 记录测试开始时的配置
    results: List[Result] = []
    log_items = []  # (marker, requested_effort, size_before, Result)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 70)
    print(f"  {profile['display_name']} reasoning_effort Benchmark  {now}  (profile={profile['name']})")
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
                    size_before = os.path.getsize(profile["log_file"])
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
    verify_effort_batch(log_items, profile["log_file"])
    return results, cfg


def gen_report(results: List[Result], cfg: dict, profile: dict,
               effort: str = BENCH_EFFORT,
               max_tokens: int = BENCH_MAX_TOKENS) -> str:
    models = [(profile["display_name"], profile["openai_model"])]
    models_label = ", ".join(dn for dn, _ in models)
    L = []
    L.append(f"# Qwen 编码能力 & 效率基准测试 ({models_label}, profile={profile['name']})")
    L.append("")
    L.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"硬件: RTX 5090D 24G")
    L.append(f"服务端: llama-swap @ {API_URL} -> llama-server :{cfg.get('port')}")
    L.append(f"每任务运行: {NUM_RUNS} 次")
    L.append(f"reasoning_effort: {effort}  |  max_tokens: {max_tokens}")
    L.append("")
    L.append(config_header_md(cfg, profile))
    L.append("> \\* 速度为客户端估算: 生成速度=输出Tok/首Tok后耗时, Prompt速度=输入Tok/首Tok延迟; 总Tok 来自 API usage (精确)。")
    L.append("> 推理词数/代码词数为按空格分词的估算值 (非精确token数); 通过率仅统计 verify=True 的任务。")
    L.append("")

    for dn, mid in models:
        mr = [r for r in results if r.model == dn and not r.error]
        if not mr:
            L.append(f"## {dn} -- 无数据")
            L.append("")
            continue

        L.append(f"## {dn}")
        L.append("")
        L.append(
            "| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) "
            "| 推理词数(估) | 代码词数(估) | 总Tok | 生成Tok/s* | 通过 |"
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
        verify_runs = [r for r in mr if r.verify]
        passed = sum(1 for r in verify_runs if r.code_pass)

        L.append("")
        L.append(
            f"**均值**: TTFT推理={statistics.mean(ttft_rs):.2f}s, "
            f"TTFT代码={statistics.mean(ttft_cs):.2f}s, "
            f"总耗时={statistics.mean(totals):.2f}s, "
            f"推理词数(估)={statistics.mean(r_toks):.0f}, "
            f"代码词数(估)={statistics.mean(c_toks):.0f}, "
            f"服务端Tok/s={statistics.mean(tpss):.1f}, "
            f"PromptTok/s={statistics.mean(p_tps):.1f}, "
            f"通过率={passed}/{len(verify_runs)} (仅verify任务)"
        )
        L.append("")

    # Comparison
    L.append("## 对比总结")
    L.append("")

    model_names = [dn for dn, _ in models]
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
        ("r_tok", "推理词数(估)"),
        ("c_tok", "代码词数(估)"),
        ("pass", "代码通过率(仅verify)"),
    ]:
        vals = []
        for dn2, mid2 in models:
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
                verify_runs2 = [r for r in mr2 if r.verify]
                pass_count = sum(1 for r in verify_runs2 if r.code_pass)
                p = pass_count / len(verify_runs2) if verify_runs2 else 0
                vals.append(f"{p:.0%} ({pass_count}/{len(verify_runs2)})")
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


def gen_effort_report(results: List[Result], cfg: dict, profile: dict) -> str:
    L = []
    L.append(f"# {profile['display_name']} reasoning_effort 性能基准测试 (profile={profile['name']})")
    L.append("")
    L.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"服务端: llama-swap @ {API_URL} -> llama-server :{cfg.get('port')}")
    L.append(f"模型: {profile['display_name']}  |  任务: {', '.join(EFFORT_TASK_NAMES)}  |  每档运行 {EFFORT_NUM_RUNS} 次")
    L.append("")
    L.append("> 指标: 推理Tok=thinking 词数, 推理耗时≈TTFT代码-TTFT推理, 总Tok 来自 API usage (精确)。")
    L.append("> 切换确认: 主信号=行为 (各档推理量差异); 辅证=日志渲染出的 effort 指令 (best-effort, 异步 flush)。")
    L.append("")

    # Part 3: 配置原样记录
    L.append(config_header_md(cfg, profile))

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
    ap.add_argument("--effort", default=BENCH_EFFORT,
                    help=f"ability 模式的 reasoning_effort (默认 {BENCH_EFFORT}; "
                         f"可选 low/medium/high/xhigh)")
    ap.add_argument("--max-tokens", type=int, default=BENCH_MAX_TOKENS,
                    help=f"ability 模式的 max_tokens (默认 {BENCH_MAX_TOKENS})")
    ap.add_argument("--profile",
                    help="只测这个 profile (bench_config.PROFILES 的 key); 默认按 ACTIVE 全量列表")
    args = ap.parse_args()

    profiles = [get_profile(args.profile)] if args.profile else active_profiles()
    print(f"  待测 profile: {[p['name'] for p in profiles]}  "
          f"(共 {len(profiles)} 个, 间隔 {PAUSE_SECONDS}s)")

    for i, profile in enumerate(profiles):
        # 结果按天存放: results/YYYY-MM-DD/<prefix>_<profile>_<ts>.{md,json}
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        out_dir = OUTPUT_DIR / now.strftime("%Y-%m-%d")
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'#' * 70}")
        print(f"# profile {i + 1}/{len(profiles)}: {profile['name']} "
              f"({profile['display_name']})")
        print(f"{'#' * 70}")

        if args.mode == "effort":
            results, cfg = run_effort_bench(profile)
            txt = gen_effort_report(results, cfg, profile)
            prefix = "effort"
        else:
            cfg = read_qwen38_config(profile)
            results = run_bench(profile, effort=args.effort,
                                max_tokens=args.max_tokens)
            txt = gen_report(results, cfg, profile, effort=args.effort,
                             max_tokens=args.max_tokens)
            prefix = "benchmark"

        md = out_dir / f"{prefix}_{profile['name']}_{ts}.md"
        md.write_text(txt, encoding="utf-8")

        jp = out_dir / f"{prefix}_{profile['name']}_{ts}.json"
        jd = []
        for r in results:
            jd.append({
                "task": r.task,
                "difficulty": r.diff,
                "model": r.model,
                "run": r.run,
                "profile": profile["name"],
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

        # 测完一个, 停顿 PAUSE_SECONDS 秒再测下一个 (最后一个不停)
        if i < len(profiles) - 1:
            print(f"\n  停顿 {PAUSE_SECONDS}s 后测试下一个 profile ...", flush=True)
            time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
