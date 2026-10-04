# Qwen 编码能力 & 效率基准测试

针对本地 llama-swap 服务（Anthropic 兼容 API）上的 Qwen 模型，进行代码生成能力与推理效率的自动化基准测试。

对比指标包括：

- **能力**：生成代码能否通过实际执行验证（`python -c` 运行，含超时保护）
- **效率**：TTFT（推理首字 / 代码首字延迟）、总耗时、生成速度 (tok/s)、Prompt 处理速度 (tok/s)、推理/代码 Token 数

## 环境要求

- Python 3.12+
- 本地 llama-swap 服务运行中（Anthropic 兼容，`POST /v1/messages`）
- 依赖：`requests`

## 安装

```bash
# 方式一：使用 uv（推荐）
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python requests

# 方式二：标准 venv（Debian/Ubuntu 需先 apt install python3.12-venv）
python3 -m venv .venv
.venv/bin/pip install requests
```

## 使用

```bash
source .venv/bin/activate
python model_bench.py                 # 编码能力全量测试 (默认 effort=xhigh)
python model_bench.py --effort medium # 指定 ability 模式的 reasoning_effort
python model_bench.py --mode effort   # reasoning_effort 性能测试 (3任务×3档×2次)
```

默认配置（生成参数在 `model_bench.py` 顶部，模型在 `bench_config.py`）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `API_URL` | `http://localhost:5807/v1/messages` | llama-swap 端点 |
| 模型 | `qwen3.8-27b` | 由 `bench_config.py` 的 `ACTIVE` profile 决定（见下） |
| `NUM_RUNS` | `3` | 每任务每模型运行次数 |
| `GEN_KWARGS` | `temp=0.3, top_p=0.9, max_tokens=4096` | 生成参数（`max_tokens` 会被 `--max-tokens` 覆盖，实际默认 16384） |
| `--effort` | `xhigh` | ability 模式 `reasoning_effort`（可选 low/medium/high/xhigh） |
| `--max-tokens` | `16384` | ability 模式 `max_tokens`（xhigh thinking 可达数千 token，需留足余量给代码） |

> 注意：
> - llama-swap 切换模型时可能返回 502，脚本会自动等待 60s 后重试一次。
> - llama-swap 有 TTL，空闲后 llama-server 被卸载；读配置时若进程不存在，脚本会先发一个最小请求触发按需加载，再读取配置。

## 切换模型

模型相关配置集中在 `bench_config.py`，每个 profile 对应 llama-swap 里加载的一个模型：

```python
PROFILES = {
    "qwen3.8-27b-ud": {
        "display_name": "qwen3.8-27b",
        "proc_match": "Qwen3.8-27B-UD-Q4_K_XL.gguf",   # pgrep 定位 llama-server 进程
        "model_id":   "qwen3.8-27b-local",             # llama-swap model id
        "log_file":   "/home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log",
    },
    "qwen3.8-27b-nvfp4": { ... },   # NVFP4-MTP-HIGH 量化
}

ACTIVE = ["qwen3.8-27b-ud"]        # 切换模型 = 改这里 (支持列表)
PAUSE_SECONDS = 60                 # 多个 profile 之间停顿的秒数
```

- **切换模型**：把 `ACTIVE` 改成 `PROFILES` 里的 key（单个字符串或列表），`model_bench.py` 会自动用该 profile 的 `model_id` / `proc_match` / `log_file`。
- **多个 profile**：`ACTIVE = ["qwen3.8-27b-ud", "qwen3.8-27b-nvfp4"]` → 依次测试，每个测完后停顿 `PAUSE_SECONDS` 秒再测下一个，各自生成独立报告。
- **新增模型**：往 `PROFILES` 加一项，再让 `ACTIVE` 指向它。
- 报告顶部 §0 与文件名都会标注当前 `profile=...`，区分同一 `display_name` 下的不同量化。

## 测试任务

| 任务 | 难度 | 验证 |
|------|------|------|
| Fibonacci Memoization（装饰器记忆化 + 边界测试） | easy | 执行验证 |
| LRU Cache（O(1) 操作、线程安全、类型注解） | medium | 执行验证 |
| Async Task Queue（优先级调度、指数退避重试） | hard | 仅生成 |
| SQL Parser（正则解析 SELECT 语句） | hard | 执行验证 |
| HTTP Downloader（并发下载、Semaphore 限流） | hard | 仅生成 |

## 输出

结果**按天存放**在 `results/YYYY-MM-DD/` 目录，每个 profile 每次运行生成一对文件（文件名含 profile 名，多个 profile 各自独立）：

- `results/YYYY-MM-DD/benchmark_<profile>_YYYYMMDD_HHMMSS.md` — 人类可读报告（配置原样记录、reasoning_effort/max_tokens、分模型明细表、均值、对比总结、代码输出样例）
- `results/YYYY-MM-DD/benchmark_<profile>_YYYYMMDD_HHMMSS.json` — 结构化原始数据（含 profile 字段、代码/推理预览，便于二次分析）
- `results/YYYY-MM-DD/effort_<profile>_YYYYMMDD_HHMMSS.{md,json}` — reasoning_effort 性能测试（`--mode effort`）

## 指标说明

- **TTFT推理 / TTFT代码**：请求发出到首个 thinking token / 首个 text token 的延迟
- **生成速度 (tok/s)**：客户端估算 = 输出 Token ÷ (首 token → 结束) 耗时
- **Prompt 速度 (tok/s)**：客户端估算 = 输入 Token ÷ 首 token 延迟（上界估计）
- **总 Token**：来自 API `usage.output_tokens`（精确值）
- **通过**：生成代码在 10s 超时内执行且退出码为 0
