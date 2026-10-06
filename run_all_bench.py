#!/usr/bin/env python3
"""按 profile 串行执行: 每个 profile 模型加载一次, 跑完全部启用的测试集, 再切下一个。

顺序: for profile in ACTIVE: for suite in ACTIVE_TESTS:
              python <suite 脚本> --profile <name> [该 suite 的额外参数]
这样同一模型的两个测试集共用一次加载, 避免跨测试集反复切换模型
(不再出现 "evalplus 测完 ud, model_bench 又切回 ninfer" 的往返)。

测试集选择由 ACTIVE_TESTS 控制 (同 bench_config 的 ACTIVE 思路, 改一行即可),
可用 --tests 覆盖。各测试集的额外参数用 --mb-args / --ep-args 原样透传, 例如:
  --mb-args "--effort xhigh --max-tokens 16384"
  --ep-args "--limit 5 --skip-eval"

用法:
  python run_all_bench.py                                    # 每个 profile: model_bench -> evalplus
  python run_all_bench.py --mb-args "--effort xhigh" --ep-args "--limit 5"
  python run_all_bench.py --tests evalplus --continue-on-error
"""

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

from bench_config import active_profiles

HERE = Path(__file__).parent

# 测试集 (列表顺序 = 每个 profile 内的执行顺序); 入口脚本均支持 --profile 指定单 profile
TESTS = {
    "model_bench": "model_bench.py",
    "evalplus": "evalplus_bench.py",
}

# 当前启用的测试集 —— 改这一行切换; 可用 --tests 覆盖。
# model_bench 在前: 5任务×3次很快, 先确认模型切换/加载成功, 再跑耗时较长的 evalplus 全量
ACTIVE_TESTS = ["model_bench", "evalplus"]


def main():
    ap = argparse.ArgumentParser(
        description="按 profile 串行执行 model_bench + evalplus_bench (跑完一个 profile 的所有测试集才切模型)")
    ap.add_argument("--tests",
                    help=f"启用的测试集, 逗号分隔, 覆盖 ACTIVE_TESTS (可选: {', '.join(TESTS)})")
    ap.add_argument("--mb-args", default="",
                    help="追加传给 model_bench.py 的参数, 如 '--effort xhigh --max-tokens 16384'")
    ap.add_argument("--ep-args", default="",
                    help="追加传给 evalplus_bench.py 的参数, 如 '--limit 5 --skip-eval'")
    ap.add_argument("--continue-on-error", action="store_true",
                    help="某一步失败 (非零退出码) 时不停止, 跳过该 profile 剩余测试集, 继续下一个 profile")
    args = ap.parse_args()

    tests = [t.strip() for t in args.tests.split(",")] if args.tests else ACTIVE_TESTS
    for t in tests:
        if t not in TESTS:
            ap.error(f"未知测试集 {t!r}, 可选: {list(TESTS)}")
    suite_args = {
        "model_bench": shlex.split(args.mb_args),
        "evalplus": shlex.split(args.ep_args),
    }

    profiles = active_profiles()
    print(f"  待测 profile: {[p['name'] for p in profiles]}  (依次; 一个 profile 跑完所有测试集才切下一个)")
    print(f"  每 profile 测试集: {tests}  |  "
          f"mb_args={suite_args['model_bench'] or '-'}  ep_args={suite_args['evalplus'] or '-'}")

    rc_all = 0
    for p in profiles:
        print(f"\n{'#' * 70}\n# profile: {p['name']} ({p['display_name']})\n{'#' * 70}", flush=True)
        for t in tests:
            cmd = [sys.executable, str(HERE / TESTS[t]), "--profile", p["name"]] + suite_args[t]
            print(f"\n{'=' * 70}\n# 步骤: {t}\n# {' '.join(cmd)}\n{'=' * 70}", flush=True)
            t0 = time.time()
            rc = subprocess.call(cmd)
            print(f"\n  {t} 结束: exit={rc}  耗时 {time.time() - t0:.0f}s", flush=True)
            if rc != 0:
                rc_all = rc
                if not args.continue_on_error:
                    print(f"  {t} 失败 (exit={rc}), 停止。加 --continue-on-error 可继续后续 profile。")
                    sys.exit(rc)
                # 该 profile 的模型状态未知, 跳过剩余测试集, 直接换下一个 profile
                break
    if rc_all:
        sys.exit(rc_all)


if __name__ == "__main__":
    main()
