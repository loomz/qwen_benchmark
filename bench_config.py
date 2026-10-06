"""模型配置 — 切换/选择模型只需改 ACTIVE。

调用路径 (统一): 本脚本 -> llama-swap (8080, OpenAI /v1/chat/completions) -> llama-server
  (model-proxy 5807 已停用, 所有模型统一走 llama-swap, 用 openai_model 触发按需加载/切换)

每个 profile 对应 llama-swap 里加载的一个模型, 一组模型相关配置:
  - display_name: 报告/结果里展示的名字
  - proc_match:   llama-server 进程 cmdline 中的 GGUF 文件名 (pgrep 定位进程用)
  - model_id:     已废弃 (原 model-proxy 5807 的 model-router.json 别名); 现取值与 openai_model
                  一致, 仅为兼容保留
  - openai_model: llama-swap (8080, OpenAI /v1/chat/completions) 的 model 名 (= config.yaml 的 key),
                  model_bench.py / evalplus_bench.py 均走这条路径
  - log_file:     llama-server 的 --log-file 路径 (reasoning_effort 日志校验用)

ACTIVE 支持一个或多个 profile:
  - 单个:  ACTIVE = "qwen3.8-27b-ud"
  - 多个:  ACTIVE = ["qwen3.8-27b-ud", "qwen3.8-27b-nvfp4", "qwen3.6-35b-a3b"]
           -> 依次测试, 每个测完后停顿 PAUSE_SECONDS 秒再测下一个
"""

PROFILES = {
    # UD Q4_K_XL 量化
    "qwen3.8-27b-ud": {
        "display_name": "qwen3.8-27b-ud",
        "proc_match": "Qwen3.8-27B-UD-Q4_K_XL.gguf",
        "model_id": "qwen3.8-27b-ud",
        "openai_model": "qwen3.8-27b-ud",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log",
    },
    # NVFP4 MTP-HIGH 量化
    "qwen3.8-27b-nvfp4": {
        "display_name": "qwen3.8-27b-nvfp4",
        "proc_match": "Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
        "model_id": "qwen3.8-27b-nvfp4",
        "openai_model": "qwen3.8-27b-nvfp4",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.log",
    },
    # ninfer 版本
    "qwen3.8-27b-ninfer": {
        "display_name": "qwen3.8-27b",
        "proc_match": "ninfer-serve",
        "model_id": "qwen3.8-27b",
        "openai_model": "qwen3.8-27b",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-NVFP4-ninfer.log",
    },
    # MoE 混合专家 (A3B), thinking 模型 (无 --reasoning-effort flag)
    "qwen3.6-35b-a3b": {
        "display_name": "qwen3.6-35b-a3b",
        "proc_match": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
        "model_id": "qwen3.6-35b",
        "openai_model": "qwen3.6-35b",
        "log_file": "/home/loomz/.llama.cpp/logs/Qwen3.6-35B-A3B-UD-Q4_K_M.log",
    },
}

# 当前激活的 profile —— 切换模型改这里; 支持列表 (依次测试, 间隔 PAUSE_SECONDS)
ACTIVE = ["qwen3.8-27b-ninfer","qwen3.8-27b-nvfp4","qwen3.8-27b-ud"]

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
