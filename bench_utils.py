"""共享: 模型服务进程配置发现 (model_bench.py / evalplus_bench.py 共用)。

调用路径: llama-swap (8080, OpenAI 兼容) -> 模型服务进程。
普通 profile 的进程是 llama-server (动态端口, 带 /props 运行时状态);
ninfer profile (proc_match="ninfer-serve") 的进程是 ninfer-serve —— 统一按
profile 的 proc_match 匹配, 不写死 "llama-server"。

llama-swap 有 TTL, 空闲后模型进程被卸载 -> 进程不存在; 此时先发最小请求触发
按需加载/切换, 再轮询等待进程出现。
"""

import json
import subprocess
import time

import requests

# llama-swap 的 OpenAI 端点 (与 model_bench / evalplus_bench 的 API_URL 一致)
SWAP_BASE_URL = "http://localhost:8080/v1"


def discover_qwen38(proc_match: str) -> dict:
    """定位运行中的模型服务进程 (llama-server, 或 ninfer profile 的 ninfer-serve),
    返回 {pid, cmdline, port}。
    pgrep 可能返回多个 PID (含已退出的), 只取仍存活且 cmdline 含 proc_match 的。"""
    try:
        out = subprocess.run(
            ["pgrep", "-f", proc_match],
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
        # 用 proc_match 判定进程 (覆盖 llama-server / ninfer-serve 等不同后端),
        # 而不是写死 "llama-server" —— 否则 ninfer profile 永远发现不了,
        # warm-up 会空等满 600s 超时
        if proc_match not in cmdline:
            continue
        port = None
        toks = cmdline.split()
        for i, t in enumerate(toks):
            if t == "--port" and i + 1 < len(toks):
                port = toks[i + 1]
                break
        return {"pid": pid, "cmdline": cmdline, "port": port}
    return {"error": f"no live model-server matched {proc_match}"}


def _warm_up(model_id: str, proc_match: str, base_url: str = SWAP_BASE_URL,
             timeout: int = 600) -> bool:
    """llama-swap 有 TTL, 空闲后模型进程被卸载 -> 进程不存在。
    发一个最小请求触发按需加载 (model_id 即 discover 匹配的那个),
    并轮询等待模型服务进程出现。llama-swap 加载/切换期间可能返回 502,
    故在超时窗口内持续重试 ping (有界, 每 5s 一次)。"""
    print(f"  模型服务未加载 (llama-swap TTL 已卸载), 触发按需加载 (model={model_id}) ...",
          flush=True)
    deadline = time.time() + timeout
    last_err = ""
    while time.time() < deadline:
        if "pid" in discover_qwen38(proc_match):
            print("  模型服务已加载。", flush=True)
            return True
        try:
            r = requests.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1, "stream": False,
                },
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer none"},
                timeout=30,
            )
            if r.status_code == 200:
                last_err = ""
            else:
                last_err = f"HTTP {r.status_code} (加载/切换中)"
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
        if last_err:
            print(f"  warm-up: {last_err}", flush=True)
        time.sleep(5)
    print("  warm-up 超时, 模型服务仍未出现。", flush=True)
    return False


def read_qwen38_config(profile: dict) -> dict:
    """读取当前模型服务 (llama-server / ninfer-serve) 配置: 进程 cmdline (原样) + /props (运行时)。
    llama-swap 有 TTL, 空闲后进程被卸载 -> 不存在; 此时先按需唤醒再读。"""
    disc = discover_qwen38(profile["proc_match"])
    if "pid" not in disc:
        _warm_up(profile["openai_model"], profile["proc_match"])
        disc = discover_qwen38(profile["proc_match"])
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
        except Exception as e:  # noqa: BLE001
            cfg["error"] = f"cmdline OK, /props failed: {e}"
    return cfg


def _cmdline_multiline(cmdline: str) -> str:
    """cmdline 拆多行: 可执行文件独占一行, 每个 -/-- 参数各占一行 (取值跟同一行)。"""
    toks = cmdline.split()
    if not toks:
        return cmdline
    lines = [toks[0]]
    cur = None
    for t in toks[1:]:
        if t.startswith("-"):
            if cur is not None:
                lines.append("  " + cur)
            cur = t
        else:
            cur = f"{cur} {t}" if cur else t
    if cur is not None:
        lines.append("  " + cur)
    return "\n".join(lines)


def config_header_md(cfg: dict, profile: dict) -> str:
    """报告章节: 原样记录当前模型服务 (llama-server; ninfer profile 为 ninfer-serve) 的配置。"""
    L = []
    L.append(f"## 0. 当前模型服务配置 ({profile['display_name']}, profile={profile['name']}, 原样记录)")
    L.append("")
    if cfg.get("error"):
        L.append(f"> ⚠️ 配置读取: {cfg['error']}")
        L.append("")
    if cfg.get("cmdline"):
        L.append(f"**进程** (PID {cfg.get('pid')}, port {cfg.get('port')}):")
        L.append("")
        L.append("```bash")
        L.append(_cmdline_multiline(cfg["cmdline"]))
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
