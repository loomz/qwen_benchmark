# EvalPlus HumanEval+ 基准测试报告

- **profile**: `qwen3.8-27b-ud`  (display: qwen3.8-27b)
- **openai_model (llama-swap)**: `qwen3.8-27b`
- **端点 base_url**: `http://localhost:8080/v1`
- **数据集**: humaneval (HumanEval+ 增强测试用例)
- **解码**: greedy (temp=0)
- **max_tokens**: 2048
- **题目数**: 2 (limit=2)
- **模型加载耗时 (warmup)**: 0.8s
- **时间**: 2026-10-05 01:32:50

## 汇总

| 指标 | 值 |
|------|-----|
| 总生成时间 (Σ decode) | 13.4s |
| 总输出 tokens | 2147 |
| 整体生成速度 (Σtok/Σt) | 160.7 tok/s |
| 生成速度 tok/s (mean/median/min/max) | 152.9 / 152.9 / 150.3 / 155.5 |
| 平均每题输出 tokens | 1073.5 |
| 平均每题 prompt tokens | 153.0 |

## 每题明细

| task_id | base | plus | 输出tok | 生成时间(s) | 生成tok/s |
|---|---|---|---|---|---|
| HumanEval/0 | - | - | 1045 | 6.4 | 155.5 |
| HumanEval/1 | - | - | 1102 | 7.0 | 150.3 |

## 说明

- evalplus 0.3.1 的输出不含逐题时间戳, 生成时间/token 数在生成时直接从 llama-server OpenAI 响应的 `usage` + `timings` 捕获。
- **生成 tok/s** = `timings.predicted_per_token` (decode 阶段吞吐, 含思考 token); 缺失时用 输出tokens/墙钟时间 估算。
- **pass@1 (base)**: 仅基础测试用例通过; **pass@1 (base+plus)**: 基础+增强测试全部通过。
- 生成路径走 llama-swap (8080) OpenAI 端点, 用 profile 的 `openai_model` 触发按需加载/切换。