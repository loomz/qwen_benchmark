"""EvalPlus HumanEval+ 基准测试 — 独立脚本, 支持多模型 active。

能力: 用 evalplus 跑 HumanEval+ (164 题, 含增强测试用例), 得到 pass@1 (base / base+plus)。
效率: 生成时直接从 llama-server 的 OpenAI 响应 (usage + timings) 捕获每题的
      生成时间 (decode 阶段) 与 token 数, 计算生成速度 tok/s。

为什么自己驱动生成循环?
  evalplus 0.3.1 的输出 (solutions.jsonl / eval_results.json) 不含逐题时间戳,
  只有 pass/fail。因此本脚本自己跑生成循环, 逐题记录 timings/usage, 再把
  evalplus 格式的 solutions.jsonl 交给 evalplus.evaluate 打分, 最后合并出报告。

调用路径: 本脚本 -> llama-swap (8080, OpenAI /v1/chat/completions) -> llama-server
  (不走 model-proxy 5807; evalplus 用 OpenAI 后端, 且 5804 直连端口无法多模型切换,
   故统一走 llama-swap 8080, 用 profile 的 openai_model 触发按需加载/切换)。

多模型: 复用 bench_config.py 的 ACTIVE (列表) + PAUSE_SECONDS, 依次测试, 各自独立报告。

用法:
  python evalplus_bench.py                  # 全量 164 题 (humaneval)
  python evalplus_bench.py --limit 5        # 只跑前 5 题 (快速验证脚本; 自动跳过评测)
  python evalplus_bench.py --skip-eval      # 只生成不评测 (更快, 无 pass@1)
  python evalplus_bench.py --max-tokens 4096
  python evalplus_bench.py --base-url http://localhost:8080/v1
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from bench_config import active_profiles, PAUSE_SECONDS

# ---- 生成参数 (与 evalplus OpenAI 后端默认对齐, 可被 CLI 覆盖) ----
OPENAI_BASE_URL = "http://localhost:8080/v1"   # llama-swap 的 OpenAI 端点
API_KEY = "none"                               # llama-swap 不校验 key
DATASET = "humaneval"                          # HumanEval+ (164 题); 可选 mbpp
MAX_TOKENS = 2048                              # 每题生成上限 (留足余量防截断)
TEMPERATURE = 0.0                              # greedy (对应 --greedy)
REQUEST_TIMEOUT = 600                          # 单请求超时 (含可能的模型加载)
WARMUP_TIMEOUT = 600                           # warmup 请求超时
WARMUP_RETRIES = 3                             # warmup / 单题失败重试次数
OUTPUT_DIR = Path(__file__).parent / "results"

# 与 evalplus codegen.py 完全一致的 instruction 前缀
INSTRUCTION_PREFIX = (
    "Please provide a self-contained Python script that solves "
    "the following problem in a markdown code block:"
)


def build_message(prompt: str) -> str:
    """与 evalplus OpenAI 后端 (provider/openai.py) 完全一致的 prompt 构造。"""
    return INSTRUCTION_PREFIX + f"\n```python\n{prompt.strip()}\n```"


def _headers() -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}


def generate_one(session, base_url, model, message, max_tokens, temperature,
                 timeout=REQUEST_TIMEOUT, retries=2) -> dict:
    """发一次 chat/completions, 返回 {content, reasoning, output_tokens, gen_s, gen_tps, ...}。

    gen_s / gen_tps 优先取 llama-server 的 timings.predicted_ms / predicted_per_token
    (纯 decode 阶段, 含思考 token); timings 缺失时退回 wall-clock 估算。
    """
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    last_err = None
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            r = session.post(url, json=payload, headers=_headers(), timeout=timeout)
            wall = time.perf_counter() - t0
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}: {r.text[:300]}"
                if attempt < retries:
                    time.sleep(5 * (attempt + 1))
                    continue
                return {"error": last_err, "wall_s": wall}
            data = r.json()
            msg = data["choices"][0]["message"]
            usage = data.get("usage", {}) or {}
            timings = data.get("timings", {}) or {}
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""
            out_tok = usage.get("completion_tokens")
            prompt_tok = usage.get("prompt_tokens")
            gen_ms = timings.get("predicted_ms")
            prompt_ms = timings.get("prompt_ms")
            gen_tps = timings.get("predicted_per_token")
            prompt_tps = timings.get("prompt_per_token")
            # 兜底: timings 缺失时用 wall 估算
            if gen_tps is None and out_tok and wall > 0:
                gen_tps = out_tok / wall
            return {
                "content": content,
                "reasoning": reasoning,
                "output_tokens": out_tok,
                "prompt_tokens": prompt_tok,
                "gen_s": (gen_ms / 1000.0) if gen_ms is not None else wall,
                "prompt_s": (prompt_ms / 1000.0) if prompt_ms is not None else None,
                "gen_tps": gen_tps,
                "prompt_tps": prompt_tps,
                "wall_s": wall,
                "finish_reason": data["choices"][0].get("finish_reason"),
                "error": None,
            }
        except Exception as e:  # noqa: BLE001
            wall = time.perf_counter() - t0
            last_err = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
                continue
            return {"error": last_err, "wall_s": wall}
    return {"error": last_err, "wall_s": 0.0}


def ensure_loaded(session, base_url, model, timeout=WARMUP_TIMEOUT, retries=WARMUP_RETRIES):
    """发一个最小请求触发 llama-swap 按需加载/切换模型。返回 (ok, elapsed_s, detail)。"""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    t0 = time.perf_counter()
    detail = ""
    for attempt in range(retries + 1):
        try:
            r = session.post(url, json=payload, headers=_headers(), timeout=timeout)
            if r.status_code == 200:
                return True, time.perf_counter() - t0, "ok"
            detail = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa: BLE001
            detail = f"{type(e).__name__}: {e}"
        if attempt < retries:
            print(f"    warmup 重试 {attempt + 1}/{retries}: {detail}", flush=True)
            time.sleep(10)
    return False, time.perf_counter() - t0, detail


def _load_problems(dataset: str) -> dict:
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        return get_human_eval_plus()
    if dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        return get_mbpp_plus()
    raise ValueError(f"不支持的 dataset: {dataset} (可选 humaneval/mbpp)")


def run_codegen(profile, base_url, max_tokens, temperature, dataset, limit, work_dir):
    """逐题生成, 写 evalplus 格式 solutions.jsonl + 逐题 timing 侧车。返回 (records, sol_path)。"""
    from evalplus.sanitize import sanitize

    problems = _load_problems(dataset)
    items = list(problems.items())
    if limit:
        items = items[:limit]
    print(f"  生成 {len(items)} 题 (openai_model={profile['openai_model']}) ...", flush=True)

    sol_path = work_dir / "solutions.jsonl"
    timing_path = work_dir / "codegen_timing.json"
    records = []
    session = requests.Session()
    with open(sol_path, "w", encoding="utf-8") as sf:
        for i, (task_id, task) in enumerate(items):
            message = build_message(task["prompt"])
            res = generate_one(
                session, base_url, profile["openai_model"],
                message, max_tokens, temperature,
            )
            entry = {"task_id": task_id, "entry_point": task["entry_point"]}
            if res.get("error"):
                entry.update({
                    "error": res["error"], "solution": "", "raw": "", "reasoning": "",
                    "output_tokens": 0, "prompt_tokens": None,
                    "gen_s": res.get("wall_s"), "prompt_s": None,
                    "gen_tps": None, "prompt_tps": None,
                    "reasoning_chars": 0, "content_chars": 0, "finish_reason": None,
                })
            else:
                try:
                    sanitized = sanitize(res["content"], entrypoint=task["entry_point"])
                except Exception:  # noqa: BLE001  sanitize 失败则退回原始输出
                    sanitized = res["content"]
                entry.update({
                    "solution": sanitized, "raw": res["content"], "reasoning": res["reasoning"],
                    "output_tokens": res["output_tokens"], "prompt_tokens": res["prompt_tokens"],
                    "gen_s": res["gen_s"], "prompt_s": res["prompt_s"],
                    "gen_tps": res["gen_tps"], "prompt_tps": res["prompt_tps"],
                    "wall_s": res["wall_s"], "finish_reason": res["finish_reason"],
                    "reasoning_chars": len(res["reasoning"]), "content_chars": len(res["content"]),
                    "error": None,
                })
            # 无论成功/失败都写入 solutions.jsonl: 全量运行时必须覆盖全部题目,
            # 否则 evalplus.evaluate 的断言 (样本数 == 题目数) 会失败。
            # 失败题写空 solution -> 评测记为 fail (而非被静默丢弃)。
            sf.write(json.dumps({"task_id": task_id, "solution": entry["solution"]},
                                ensure_ascii=False) + "\n")
            records.append(entry)
            flag = "OK " if not res.get("error") else "ERR"
            tps = entry.get("gen_tps")
            print(f"    [{i + 1}/{len(items)}] {task_id} {flag} "
                  f"out={entry.get('output_tokens')} gen={entry.get('gen_s') or 0:.1f}s "
                  f"tps={tps if tps is None else round(tps, 1)}", flush=True)
    timing_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records, sol_path


def run_eval(solutions_path, dataset, work_dir):
    """调用 evalplus.evaluate 打分 (不重新生成)。返回 eval_results dict。"""
    from evalplus.evaluate import evaluate

    result_path = str(solutions_path).replace(".jsonl", "_eval_results.json")
    p = Path(result_path)
    if p.exists():
        p.unlink()
    print("  评测中 (evalplus.evaluate, 跑 base+plus 测试用例) ...", flush=True)
    evaluate(dataset=dataset, samples=str(solutions_path))
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt_tps(v):
    return "-" if v is None else f"{v:.1f}"


def build_report(profile, records, eval_results, base_url, max_tokens, temperature,
                 dataset, limit, warmup_s, skipped_eval) -> tuple:
    """合并 pass/fail 与逐题 timing, 返回 (markdown, json_dict)。"""
    eval_map = {}
    if eval_results:
        for task_id, lst in eval_results.get("eval", {}).items():
            if lst:
                r0 = lst[0]
                eval_map[task_id] = (r0.get("base_status"), r0.get("plus_status"))

    rows = []
    for rec in records:
        tid = rec["task_id"]
        base_st, plus_st = eval_map.get(tid, (None, None))
        rows.append({
            "task_id": tid,
            "base_pass": (base_st == "pass"),
            "plus_pass": (plus_st == "pass"),
            "base_status": base_st,
            "plus_status": plus_st,
            "output_tokens": rec.get("output_tokens") or 0,
            "prompt_tokens": rec.get("prompt_tokens"),
            "gen_s": rec.get("gen_s"),
            "gen_tps": rec.get("gen_tps"),
            "prompt_tps": rec.get("prompt_tps"),
            "reasoning_chars": rec.get("reasoning_chars", 0),
            "content_chars": rec.get("content_chars", 0),
            "error": rec.get("error"),
        })

    n = len(rows)
    base_pass_n = sum(1 for r in rows if r["base_pass"])
    plus_pass_n = sum(1 for r in rows if r["plus_pass"])
    pass_at_1_base = (base_pass_n / n) if n else 0.0
    pass_at_1_plus = (plus_pass_n / n) if n else 0.0

    tps_list = [r["gen_tps"] for r in rows if r["gen_tps"] is not None]
    gen_s_list = [r["gen_s"] for r in rows if r["gen_s"] is not None]
    out_tok_list = [r["output_tokens"] for r in rows if r["output_tokens"]]
    prompt_tok_list = [r["prompt_tokens"] for r in rows if r["prompt_tokens"]]
    total_gen_s = sum(gen_s_list)
    total_out_tok = sum(out_tok_list)
    n_err = sum(1 for r in rows if r["error"])

    def _stat(lst):
        if not lst:
            return {"mean": None, "median": None, "min": None, "max": None}
        return {
            "mean": statistics.fmean(lst),
            "median": statistics.median(lst),
            "min": min(lst),
            "max": max(lst),
        }

    tps_stat = _stat(tps_list)
    summary = {
        "profile": profile["name"],
        "display_name": profile["display_name"],
        "openai_model": profile["openai_model"],
        "base_url": base_url,
        "dataset": dataset,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "greedy": temperature == 0.0,
        "limit": limit,
        "n_problems": n,
        "n_errors": n_err,
        "pass_at_1_base": pass_at_1_base,
        "pass_at_1_plus": pass_at_1_plus,
        "base_pass": base_pass_n,
        "plus_pass": plus_pass_n,
        "total_gen_s": total_gen_s,
        "total_output_tokens": total_out_tok,
        "overall_gen_tps": (total_out_tok / total_gen_s) if total_gen_s else None,
        "gen_tps": tps_stat,
        "mean_output_tokens": (sum(out_tok_list) / len(out_tok_list)) if out_tok_list else None,
        "mean_prompt_tokens": (sum(prompt_tok_list) / len(prompt_tok_list)) if prompt_tok_list else None,
        "warmup_s": warmup_s,
        "skipped_eval": skipped_eval,
    }

    # ---- markdown ----
    L = []
    L.append("# EvalPlus HumanEval+ 基准测试报告\n")
    L.append(f"- **profile**: `{profile['name']}`  (display: {profile['display_name']})")
    L.append(f"- **openai_model (llama-swap)**: `{profile['openai_model']}`")
    L.append(f"- **端点 base_url**: `{base_url}`")
    L.append(f"- **数据集**: {dataset} (HumanEval+ 增强测试用例)")
    L.append(f"- **解码**: {'greedy (temp=0)' if temperature == 0.0 else f'temp={temperature}'}")
    L.append(f"- **max_tokens**: {max_tokens}")
    L.append(f"- **题目数**: {n}" + (f" (limit={limit})" if limit else ""))
    L.append(f"- **模型加载耗时 (warmup)**: {warmup_s:.1f}s")
    L.append(f"- **时间**: {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    L.append("## 汇总\n")
    L.append("| 指标 | 值 |")
    L.append("|------|-----|")
    if not skipped_eval:
        L.append(f"| pass@1 (base) | {pass_at_1_base:.3f}  ({base_pass_n}/{n}) |")
        L.append(f"| pass@1 (base+plus) | {pass_at_1_plus:.3f}  ({plus_pass_n}/{n}) |")
    L.append(f"| 总生成时间 (Σ decode) | {total_gen_s:.1f}s |")
    L.append(f"| 总输出 tokens | {total_out_tok} |")
    if summary["overall_gen_tps"]:
        L.append(f"| 整体生成速度 (Σtok/Σt) | {summary['overall_gen_tps']:.1f} tok/s |")
    if tps_stat["mean"] is not None:
        L.append(f"| 生成速度 tok/s (mean/median/min/max) | "
                 f"{tps_stat['mean']:.1f} / {tps_stat['median']:.1f} / "
                 f"{tps_stat['min']:.1f} / {tps_stat['max']:.1f} |")
    if summary["mean_output_tokens"] is not None:
        L.append(f"| 平均每题输出 tokens | {summary['mean_output_tokens']:.1f} |")
    if summary["mean_prompt_tokens"] is not None:
        L.append(f"| 平均每题 prompt tokens | {summary['mean_prompt_tokens']:.1f} |")
    if n_err:
        L.append(f"| 生成失败题数 | {n_err} |")
    L.append("")

    L.append("## 每题明细\n")
    hdr = "| task_id | base | plus | 输出tok | 生成时间(s) | 生成tok/s |"
    L.append(hdr)
    L.append("|" + "---|" * 6)
    for r in rows:
        base_c = "✅" if r["base_pass"] else ("❌" if r["base_status"] else "-")
        plus_c = "✅" if r["plus_pass"] else ("❌" if r["plus_status"] else "-")
        gen_s = f"{r['gen_s']:.1f}" if r["gen_s"] is not None else "-"
        L.append(f"| {r['task_id']} | {base_c} | {plus_c} | {r['output_tokens']} "
                 f"| {gen_s} | {_fmt_tps(r['gen_tps'])} |")
    L.append("")

    L.append("## 说明\n")
    L.append("- evalplus 0.3.1 的输出不含逐题时间戳, 生成时间/token 数在生成时直接从 "
             "llama-server OpenAI 响应的 `usage` + `timings` 捕获。")
    L.append("- **生成 tok/s** = `timings.predicted_per_token` (decode 阶段吞吐, 含思考 token); "
             "缺失时用 输出tokens/墙钟时间 估算。")
    L.append("- **pass@1 (base)**: 仅基础测试用例通过; **pass@1 (base+plus)**: 基础+增强测试全部通过。")
    L.append("- 生成路径走 llama-swap (8080) OpenAI 端点, 用 profile 的 `openai_model` 触发按需加载/切换。")
    return "\n".join(L), {"summary": summary, "rows": rows}


def main():
    ap = argparse.ArgumentParser(description="EvalPlus HumanEval+ 基准测试 (多模型)")
    ap.add_argument("--base-url", default=OPENAI_BASE_URL, help="llama-swap OpenAI 端点")
    ap.add_argument("--dataset", default=DATASET, choices=["humaneval", "mbpp"])
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--temperature", type=float, default=TEMPERATURE)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 题 (0=全量)")
    ap.add_argument("--skip-eval", action="store_true", help="只生成不评测 (跳过 pass@1)")
    args = ap.parse_args()

    # evalplus.evaluate 要求样本覆盖数据集全部题目, 故 --limit (部分题) 无法打分 -> 自动跳过评测
    skip_eval = args.skip_eval or bool(args.limit)
    if args.limit and not args.skip_eval:
        print(f"  注意: --limit {args.limit} 只生成部分题, evalplus 无法对部分集打分, 自动跳过评测 (pass@1)。")

    profiles = active_profiles()
    print(f"  待测 profile: {[p['name'] for p in profiles]}  (共 {len(profiles)} 个, 间隔 {PAUSE_SECONDS}s)")
    print(f"  base_url={args.base_url}  dataset={args.dataset}  max_tokens={args.max_tokens}  "
          f"temp={args.temperature}  limit={args.limit or '全量'}  skip_eval={skip_eval}")

    for i, profile in enumerate(profiles):
        print(f"\n{'=' * 70}\n# profile {i + 1}/{len(profiles)}: {profile['name']}\n{'=' * 70}", flush=True)
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        day_dir = OUTPUT_DIR / now.strftime("%Y-%m-%d")
        work_dir = day_dir / f"evalplus_{profile['name']}_{ts}"
        work_dir.mkdir(parents=True, exist_ok=True)

        session = requests.Session()
        ok, warmup_s, detail = ensure_loaded(session, args.base_url, profile["openai_model"])
        if not ok:
            print(f"  ⚠️ 模型加载失败, 跳过该 profile: {detail}", flush=True)
            continue
        print(f"  模型就绪 (warmup {warmup_s:.1f}s)", flush=True)

        records, sol_path = run_codegen(
            profile, args.base_url, args.max_tokens, args.temperature,
            args.dataset, args.limit, work_dir,
        )

        eval_results = None
        if not skip_eval:
            try:
                eval_results = run_eval(sol_path, args.dataset, work_dir)
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ 评测失败: {e}", flush=True)
                eval_results = None

        md, js = build_report(
            profile, records, eval_results, args.base_url, args.max_tokens,
            args.temperature, args.dataset, args.limit, warmup_s,
            skip_eval or eval_results is None,
        )
        (work_dir / "report.md").write_text(md, encoding="utf-8")
        (work_dir / "report.json").write_text(json.dumps(js, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
        print(f"\n  报告: {work_dir / 'report.md'}")
        s = js["summary"]
        m = s["gen_tps"]["mean"]
        m_str = f"{m:.1f}" if m else "-"
        if not s["skipped_eval"]:
            print(f"  pass@1 base={s['pass_at_1_base']:.3f}  base+plus={s['pass_at_1_plus']:.3f}  "
                  f"gen_tps(mean)={m_str}")
        else:
            print(f"  (跳过评测) gen_tps(mean)={m_str}")

        if i < len(profiles) - 1:
            print(f"\n  停顿 {PAUSE_SECONDS}s 后测试下一个 profile ...", flush=True)
            time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
