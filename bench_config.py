"""模型配置 — 切换/选择模型只需改 ACTIVE。

调用路径: model-proxy (5807) -> llama-swap (8080) -> llama-server (5804)

每个 profile 对应 llama-swap 里加载的一个模型, 一组模型相关配置:
  - display_name: 报告/结果里展示的名字
  - proc_match:   llama-server 进程 cmdline 中的 GGUF 文件名 (pgrep 定位进程用)
  - model_id:     model-proxy (5807, Anthropic /v1/messages) 的 model 名 (model-router.json 别名)
  - openai_model: llama-swap (8080, OpenAI /v1/chat/completions) 的 model 名 (= config.yaml 的 key),
                  evalplus_bench.py 走这条路径
  - log_file:     llama-server 的 --log-file 路径 (reasoning_effort 日志校验用)

注意: model_id 与 openai_model 可能不同 —— 例如 UD 量化在 model-proxy 里叫
"qwen3.8-27b-local", 但在 llama-swap 里叫 "qwen3.8-27b"。

ACTIVE 支持一个或多个 profile:
  - 单个:  ACTIVE = "qwen3.8-27b-ud"
  - 多个:  ACTIVE = ["qwen3.8-27b-ud", "qwen3.8-27b-nvfp4"]
           -> 依次测试, 每个测完后停顿 PAUSE_SECONDS 秒再测下一个
"""

PROFILES = {
    # UD Q4_K_XL 量化
    "qwen3.8-27b-ud": {
        "display_name": "qwen3.8-27b",
        "proc_match": "Qwen3.8-27B-UD-Q4_K_XL.gguf",
        "model_id": "qwen3.8-27b-local",
        "openai_model": "qwen3.8-27b",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log",
    },
    # NVFP4 MTP-HIGH 量化
    "qwen3.8-27b-nvfp4": {
        "display_name": "qwen3.8-27b",
        "proc_match": "Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
        "model_id": "qwen3.8-27b-nvfp4",
        "openai_model": "qwen3.8-27b-nvfp4",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.log",
    },
}

# 当前激活的 profile —— 切换模型改这里; 支持列表 (依次测试, 间隔 PAUSE_SECONDS)
ACTIVE = ["qwen3.8-27b-ud", "qwen3.8-27b-nvfp4"]

# 多个 profile 之间停顿的秒数 (测完一个, 等这么久再测下一个)
PAUSE_SECONDS = 60


def get_profile(name: str) -> dict:
    """返回 profile dict (额外带 name 字段)。name 不存在时抛 KeyError。"""
    if name not in PROFILES:
        raise KeyError(f"{name!r} 不在 PROFILES 中, 可选: {list(PROFILES)}")
    p = dict(PROFILES[name])
    p["name"] = name
    return p


def active_profiles() -> list:
    """把 ACTIVE 归一化为 profile dict 列表 (支持单个字符串或列表)。"""
    names = ACTIVE if isinstance(ACTIVE, (list, tuple)) else [ACTIVE]
    return [get_profile(n) for n in names]
