# Qwen 编码能力 & 效率基准测试 (qwen3.8-27b-nvfp4, profile=qwen3.8-27b-nvfp4)

时间: 2026-10-06 04:37:06
硬件: RTX 5090D 24G
服务端: llama-swap @ http://localhost:8080/v1/chat/completions -> llama-server :5805
每任务运行: 3 次
reasoning_effort: medium  |  max_tokens: 16384

## 0. 当前 llama-server 配置 (qwen3.8-27b-nvfp4, profile=qwen3.8-27b-nvfp4, 原样记录)

**进程** (PID 48327, port 5805):

```bash
/home/loomz/.llama.cpp/llama.cpp/build/bin/llama-server
  -m /home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf
  --log-file /home/loomz/.llama.cpp/logs/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf.log
  --host 0.0.0.0
  --port 5805
  -c 150000
  -ctk q8_0
  -ctv turbo4
  -ngl 999
  -t 8
  -b 4096
  -ub 2048
  --flash-attn on
  --no-mmap
  --jinja
  --chat-template-file /home/loomz/.llama.cpp/llama-swap/qwen3.8-tolerant-sys.jinja
  --reasoning-effort medium
  --prio 2
  --parallel 1
  --cache-reuse 256
  --temp 0.6
  --top-k 20
  --top-p 0.9
  --min-p 0.0
  --samplers top_k;top_p;temperature
  --spec-type draft-mtp
  --spec-draft-n-max 4
  --cache-type-k-draft q4_0
  --cache-type-v-draft q4_0
```

**/props (运行时状态, 原样):**

```json
{
  "default_generation_settings": {
    "params": {
      "seed": 4294967295,
      "temperature": 0.6000000238418579,
      "dynatemp_range": 0.0,
      "dynatemp_exponent": 1.0,
      "top_k": 20,
      "top_p": 0.8999999761581421,
      "min_p": 0.0,
      "top_n_sigma": -1.0,
      "xtc_probability": 0.0,
      "xtc_threshold": 0.10000000149011612,
      "typical_p": 1.0,
      "repeat_last_n": 64,
      "repeat_penalty": 1.0,
      "presence_penalty": 0.0,
      "frequency_penalty": 0.0,
      "dry_multiplier": 0.0,
      "dry_base": 1.75,
      "dry_allowed_length": 2,
      "dry_penalty_last_n": 64,
      "mirostat": 0,
      "mirostat_tau": 5.0,
      "mirostat_eta": 0.10000000149011612,
      "adaptive_target": -1.0,
      "adaptive_decay": 0.8999999761581421,
      "max_tokens": -1,
      "n_predict": -1,
      "n_keep": 0,
      "n_discard": 0,
      "ignore_eos": false,
      "stream": false,
      "n_probs": 0,
      "min_keep": 0,
      "chat_format": "Content-only",
      "reasoning_format": "none",
      "reasoning_in_content": false,
      "generation_prompt": "",
      "samplers": [
        "top_k",
        "top_p",
        "temperature"
      ],
      "speculative.types": "none",
      "timings_per_token": false,
      "post_sampling_probs": false,
      "backend_sampling": false,
      "lora": []
    },
    "n_ctx": 150016
  },
  "total_slots": 1,
  "model_alias": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
  "model_ftype": "Q8_0",
  "model_path": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
  "modalities": {
    "vision": false,
    "video": false,
    "audio": false
  },
  "media_marker": "<__media_RdntAN00VePDtGpponcp4cbp5Ak8Nfzi__>",
  "endpoint_slots": true,
  "endpoint_props": false,
  "endpoint_metrics": false,
  "ui": true,
  "ui_settings": {},
  "chat_template": "{%- set image_count = namespace(value=0) %}\n{%- set video_count = namespace(value=0) %}\n{%- macro render_content(content, do_vision_count, is_system_content=false) %}\n    {%- if content is string %}\n        {{- content }}\n    {%- elif content is iterable and content is not mapping %}\n        {%- for item in content %}\n            {%- if 'image' in item or 'image_url' in item or item.type == 'image' %}\n                {%- if is_system_content %}\n                    {{- raise_exception('System message cannot contain images.') }}\n                {%- endif %}\n                {%- if do_vision_count %}\n                    {%- set image_count.value = image_count.value + 1 %}\n                {%- endif %}\n                {%- if add_vision_id %}\n                    {{- 'Picture ' ~ image_count.value ~ ': ' }}\n                {%- endif %}\n                {{- '<|vision_start|><|image_pad|><|vision_end|>' }}\n            {%- elif 'video' in item or item.type == 'video' %}\n                {%- if is_system_content %}\n                    {{- raise_exception('System message cannot contain videos.') }}\n                {%- endif %}\n                {%- if do_vision_count %}\n                    {%- set video_count.value = video_count.value + 1 %}\n                {%- endif %}\n                {%- if add_vision_id %}\n                    {{- 'Video ' ~ video_count.value ~ ': ' }}\n                {%- endif %}\n                {{- '<|vision_start|><|video_pad|><|vision_end|>' }}\n            {%- elif 'text' in item %}\n                {{- item.text }}\n            {%- else %}\n                {{- raise_exception('Unexpected item type in content.') }}\n            {%- endif %}\n        {%- endfor %}\n    {%- elif content is none or content is undefined %}\n        {{- '' }}\n    {%- else %}\n        {{- raise_exception('Unexpected content type.') }}\n    {%- endif %}\n{%- endmacro %}\n{%- if not messages %}\n    {{- raise_exception('No messages provided.') }}\n{%- endif %}\n{%- set sysns = namespace(count=0, text='') %}\n{%- for message in messages %}\n    {%- if message.role == 'system' or message.role == 'developer' %}  {# tolerant: collect system msgs anywhere #}\n        {%- set sys_content = render_content(message.content, false, true)|trim %}\n        {%- if sys_content %}\n            {%- set sysns.text = sysns.text + ('\\n' if sysns.text else '') + sys_content %}\n        {%- endif %}\n        {%- set sysns.count = sysns.count + 1 %}\n    {%- endif %}\n{%- endfor %}\n{%- set num_sys = sysns.count %}\n{%- set merged_system = sysns.text %}\n{%- set reasoning_instructions = '' %}\n{%- if enable_thinking is undefined or enable_thinking is true %}\n    {%- set resolved_reasoning_effort = reasoning_effort|default('medium', true) %}\n    {%- if resolved_reasoning_effort == 'high' %}\n        {%- set resolved_reasoning_effort = 'xhigh' %}\n    {%- endif %}\n    {%- if resolved_reasoning_effort not in ('xhigh', 'medium', 'low') %}\n        {{- raise_exception('Unexpected reasoning effort ' ~ reasoning_effort ~ '. Supported types are xhigh (default), medium, and low.') }}\n    {%- endif %}\n    {%- if resolved_reasoning_effort == 'xhigh' %}\n        {%- set reasoning_instructions = 'Reasoning effort is set to xhigh. Please think carefully through the task, validate key assumptions, consider plausible alternatives, and prioritize correctness, consistency, and clarity in the final answer.' %}\n    {%- elif resolved_reasoning_effort == 'low' %}\n        {%- set reasoning_instructions = 'Reasoning effort is set to low. Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.' %}\n    {%- endif %}\n{%- endif %}\n{%- if tools and tools is iterable and tools is not mapping %}\n    {{- '<|im_start|>system\\n' }}\n    {%- if reasoning_instructions %}\n        {{- reasoning_instructions + '\\n\\n' }}\n    {%- endif %}\n    {{- \"# Tools\\n\\nYou have access to the following functions:\\n\\n<tools>\" }}\n    {%- for tool in tools %}\n        {{- \"\\n\" }}\n        {{- tool | tojson }}\n    {%- endfor %}\n    {{- \"\\n</tools>\" }}\n    {{- '\\n\\nIf you choose to call a function ONLY reply in the following format with NO suffix:\\n\\n<tool_call>\\n<function=example_function_name>\\n<parameter=example_parameter_1>\\nvalue_1\\n</parameter>\\n<parameter=example_parameter_2>\\nThis is the value for the second parameter\\nthat can span\\nmultiple lines\\n</parameter>\\n</function>\\n</tool_call>\\n\\n<IMPORTANT>\\nReminder:\\n- Function calls MUST follow the specified format: an inner <function=...></function> block must be nested within <tool_call></tool_call> XML tags\\n- Required parameters MUST be specified\\n- You may provide optional reasoning for your function call in natural language BEFORE the function call, but NOT after\\n- If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls\\n</IMPORTANT>' }}\n    {%- if merged_system %}\n        {{- '\\n\\n' + merged_system }}\n    {%- endif %}\n    {{- '<|im_end|>\\n' }}\n{%- else %}\n    {%- if merged_system %}\n        {{- '<|im_start|>system\\n' + (reasoning_instructions + '\\n\\n' if reasoning_instructions else '')  + merged_system + '<|im_end|>\\n' }}\n    {%- elif reasoning_instructions %}\n        {{- '<|im_start|>system\\n' + reasoning_instructions + '<|im_end|>\\n' }}\n    {%- endif %}\n{%- endif %}\n{%- set ns = namespace(multi_step_tool=true, last_query_index=messages|length - 1) %}\n{%- for message in messages[::-1] %}\n    {%- set index = (messages|length - 1) - loop.index0 %}\n    {%- if ns.multi_step_tool and message.role == \"user\" %}\n        {%- set content = render_content(message.content, false)|trim %}\n        {%- if not(content.startswith('<tool_response>') and content.endswith('</tool_response>')) %}\n            {%- set ns.multi_step_tool = false %}\n            {%- set ns.last_query_index = index %}\n        {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- for message in messages %}\n    {%- if message.role != \"system\" and message.role != \"developer\" %}  {# tolerant: system msgs merged above, skip here #}\n    {%- set content = render_content(message.content, true)|trim %}\n    {%- if message.role == \"user\" %}\n        {{- '<|im_start|>' + message.role + '\\n' + content + '<|im_end|>' + '\\n' }}\n    {%- elif message.role == \"assistant\" %}\n        {%- set reasoning_content = '' %}\n        {%- if message.reasoning_content is string %}\n            {%- set reasoning_content = message.reasoning_content %}\n        {%- endif %}\n        {%- set reasoning_content = reasoning_content|trim %}\n        {%- if preserve_thinking is undefined or preserve_thinking is true or loop.index0 > ns.last_query_index %}\n            {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content + '\\n</think>\\n\\n' + content }}\n        {%- else %}\n            {{- '<|im_start|>' + message.role + '\\n' + content }}\n        {%- endif %}\n        {%- if message.tool_calls and message.tool_calls is iterable and message.tool_calls is not mapping %}\n            {%- for tool_call in message.tool_calls %}\n                {%- if tool_call.function is defined %}\n                    {%- set tool_call = tool_call.function %}\n                {%- endif %}\n                {%- if tool_call.name is not defined or tool_call.name is none %}\n                    {{- raise_exception('Tool call is missing a function name.') }}\n                {%- endif %}\n                {%- if loop.first %}\n                    {%- if content|trim %}\n                        {{- '\\n\\n<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                    {%- else %}\n                        {{- '<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                    {%- endif %}\n                {%- else %}\n                    {{- '\\n<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                {%- endif %}\n                {%- if tool_call.arguments is mapping %}\n                    {%- for args_name, args_value in tool_call.arguments|items %}\n                        {{- '<parameter=' + args_name + '>\\n' }}\n                        {%- set args_value = args_value | string if args_value is string else args_value | tojson | safe %}\n                        {{- args_value }}\n                        {{- '\\n</parameter>\\n' }}\n                    {%- endfor %}\n                {%- elif tool_call.arguments is string %}\n                    {%- if tool_call.arguments|trim %}\n                        {{- raise_exception('Tool call arguments for function \"' + (tool_call.name | string) + '\" were passed as a JSON string. Parse them into an object before calling apply_chat_template.') }}\n                    {%- endif %}\n                {%- elif tool_call.arguments is defined and tool_call.arguments is not none %}\n                    {{- raise_exception('Tool call arguments for function \"' + (tool_call.name | string) + '\" must be an object/mapping or a JSON string.') }}\n                {%- endif %}\n                {{- '</function>\\n</tool_call>' }}\n            {%- endfor %}\n        {%- endif %}\n        {{- '<|im_end|>\\n' }}\n    {%- elif message.role == \"tool\" %}\n        {%- if loop.previtem and loop.previtem.role != \"tool\" %}\n            {{- '<|im_start|>user' }}\n        {%- endif %}\n        {{- '\\n<tool_response>\\n' }}\n        {{- content }}\n        {{- '\\n</tool_response>' }}\n        {%- if not loop.last and loop.nextitem.role != \"tool\" %}\n            {{- '<|im_end|>\\n' }}\n        {%- elif loop.last %}\n            {{- '<|im_end|>\\n' }}\n        {%- endif %}\n    {%- else %}\n        {{- raise_exception('Unexpected message role.') }}\n    {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- if add_generation_prompt %}\n    {{- '<|im_start|>assistant\\n' }}\n    {%- if enable_thinking is defined and enable_thinking is false %}\n        {{- '<think>\\n\\n</think>\\n\\n' }}\n    {%- else %}\n        {{- '<think>\\n' }}\n    {%- endif %}\n{%- endif %}\n{#- Unsloth fixes - developer role, merged system messages, tool calling #}",
  "chat_template_caps": {
    "supports_object_arguments": true,
    "supports_parallel_tool_calls": true,
    "supports_preserve_reasoning": true,
    "supports_reasoning_effort": true,
    "supports_string_content": true,
    "supports_system_role": true,
    "supports_tool_calls": true,
    "supports_tools": true,
    "supports_typed_content": false
  },
  "bos_token": "<|endoftext|>",
  "eos_token": "<|im_end|>",
  "build_info": "b10837-bcb85fc3a",
  "is_sleeping": false,
  "cors_proxy_enabled": false
}
```

> \* 速度为客户端估算: 生成速度=输出Tok/首Tok后耗时, Prompt速度=输入Tok/首Tok延迟; 总Tok 来自 API usage (精确)。
> 推理词数/代码词数为按空格分词的估算值 (非精确token数); 通过率仅统计 verify=True 的任务。

## qwen3.8-27b-nvfp4

| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) | 推理词数(估) | 代码词数(估) | 总Tok | 生成Tok/s* | 通过 |
|------|---|-------------|-------------|----------|---------|---------|-------|-------------|------|
| Fibonacci Memoization | 1 | 0.19 | 1.76 | 2.80 | 69 | 79 | 408 | 156.1 | Y |
| Fibonacci Memoization | 2 | 0.07 | 6.28 | 7.02 | 434 | 61 | 1113 | 160.0 | Y |
| Fibonacci Memoization | 3 | 0.07 | 1.96 | 2.89 | 47 | 70 | 444 | 157.4 | Y |
| LRU Cache | 1 | 0.14 | 5.54 | 9.40 | 314 | 250 | 1629 | 176.0 | Y |
| LRU Cache | 2 | 0.07 | 5.66 | 9.74 | 317 | 261 | 1714 | 177.3 | Y |
| LRU Cache | 3 | 0.07 | 4.40 | 10.58 | 257 | 393 | 1853 | 176.2 | Y |
| Async Task Queue | 1 | 0.14 | 11.20 | 19.47 | 531 | 450 | 3223 | 166.7 | - |
| Async Task Queue | 2 | 0.07 | 6.97 | 14.51 | 314 | 410 | 2331 | 161.4 | - |
| Async Task Queue | 3 | 0.07 | 21.04 | 30.09 | 882 | 488 | 4739 | 157.8 | - |
| SQL Parser | 1 | 0.14 | 2.77 | 6.48 | 127 | 247 | 1109 | 174.9 | Y |
| SQL Parser | 2 | 0.07 | 3.17 | 7.98 | 150 | 274 | 1360 | 171.9 | Y |
| SQL Parser | 3 | 0.06 | 2.89 | 6.88 | 136 | 251 | 1166 | 171.2 | Y |
| HTTP Downloader | 1 | 0.14 | 1.10 | 4.88 | 86 | 208 | 792 | 167.1 | - |
| HTTP Downloader | 2 | 0.07 | 1.06 | 6.47 | 95 | 316 | 1083 | 169.3 | - |
| HTTP Downloader | 3 | 0.07 | 1.54 | 5.12 | 67 | 212 | 843 | 166.8 | - |

**均值**: TTFT推理=0.09s, TTFT代码=5.16s, 总耗时=9.62s, 推理词数(估)=255, 代码词数(估)=265, 服务端Tok/s=167.3, PromptTok/s=1186.1, 通过率=9/9 (仅verify任务)

## 对比总结

| 指标 | qwen3.8-27b-nvfp4 |
|------|-------|
| 首字延迟-推理 (s) | 0.09 |
| 首字延迟-代码 (s) | 5.16 |
| 总耗时 (s) | 9.62 |
| 生成速度 (tok/s)* | 167.3 |
| Prompt 速度 (tok/s)* | 1186.1 |
| 推理词数(估) | 255 |
| 代码词数(估) | 265 |
| 代码通过率(仅verify) | 100% (9/9) |

## 代码输出样例

### qwen3.8-27b-nvfp4 - Fibonacci Memoization
**执行: PASS**

```python
```python
from functools import wraps

def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    wrapper.cache = cache
    return wrapper

@memoize
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)

assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(20) == 6765
```
```

### qwen3.8-27b-nvfp4 - LRU Cache
**执行: PASS**

```python
```python
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """Thread-safe LRU Cache with O(1) get/put."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity: int = capacity
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)


# ─── Tests ───────────────────────────────────────────────

def test_basic_eviction() -> None:
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)          # evicts key 2
    assert cache.get(2) is None
    cache.put(4, 4)          # evicts key 1
    assert cache.get(1) is None
    assert cache.get(3) == 3
    assert cache.get(4) == 4
    print("test_basic_eviction passed")


def test_update_existing_key() -> None:
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(1, 10)         # update value
    assert cache.get(1) == 10
    cache.put(2, 2)
    assert cache.get(1) == 10
    assert cache.get(2) == 2
    print("test_update_existing_key passed")


def test_thread_safety() -> None:
    cache = LRUCache(500)
    errors: list[str] = []

    def worker(start: int) -> None:
        for i in range(start, start + 100):
            cache.put(i, i)
            val = cache.get(i)
            if val is not None and val != i:
          
```

### qwen3.8-27b-nvfp4 - Async Task Queue

```python
```python
import asyncio
import heapq
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class Task:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False, default=())
    kwargs: dict = field(compare=False, default_factory=dict)
    attempts: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    next_run_time: float = field(compare=False, default=0.0)


class TaskQueueManager:
    def __init__(self, max_concurrency: int = 5, max_retries: int = 3, base_delay: float = 1.0):
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._heap: list[Task] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._running = False
        self._workers: list[asyncio.Task] = []

        # 统计
        self.completed = 0
        self.failed = 0
        self.retries = 0
        self.total_submitted = 0

    async def submit(self, func: Callable, *args, priority: int = 5, **kwargs) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            priority=priority,
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=self.max_retries,
            next_run_time=time.monotonic(),
        )
        async with self._lock:
            heapq.heappush(self._heap, task)
            self.total_submitted += 1
        return task_id

    async def _execute_task(self, task: Task):
        try:
            await task.func(*task.args, **task.kwargs)
            self.completed += 1
            print(f"  [完成] {task.id} 优先级={task.priority}")
        except Exception as e:
            task.attempts += 1
            if task.attempts <= task.max_retries:
                self.retries += 1
         
```

### qwen3.8-27b-nvfp4 - SQL Parser
**执行: PASS**

```python
```python
import re


def parse_sql(sql: str) -> dict:
    """解析简单 SQL: SELECT col FROM table WHERE cond"""
    sql = sql.strip().rstrip(';').strip()
    pattern = r'SELECT\s+(.+?)\s+FROM\s+(.+?)(?:\s+WHERE\s+(.+?))?\s*$'
    match = re.match(pattern, sql, re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot parse SQL: {sql!r}")

    selected_columns = [c.strip() for c in match.group(1).split(',')]
    table_name = match.group(2).strip()
    where_raw = match.group(3)
    where_conditions = (
        [c.strip() for c in re.split(r'\s+AND\s+', where_raw, flags=re.IGNORECASE)]
        if where_raw
        else []
    )

    return {
        'selected_columns': selected_columns,
        'table_name': table_name,
        'where_conditions': where_conditions,
    }


def test_parse_sql():
    # 基本单列
    r = parse_sql("SELECT name FROM users")
    assert r == {
        'selected_columns': ['name'],
        'table_name': 'users',
        'where_conditions': [],
    }

    # 多列
    r = parse_sql("SELECT id, name, email FROM users")
    assert r['selected_columns'] == ['id', 'name', 'email']
    assert r['table_name'] == 'users'
    assert r['where_conditions'] == []

    # 单条件
    r = parse_sql("SELECT name FROM users WHERE age > 18")
    assert r['where_conditions'] == ['age > 18']

    # 多条件 AND
    r = parse_sql("SELECT id, name FROM orders WHERE status = 'active' AND total > 100")
    assert r['selected_columns'] == ['id', 'name']
    assert r['table_name'] == 'orders'
    assert r['where_conditions'] == ["status = 'active'", 'total > 100']

    # 大小写不敏感
    r = parse_sql("select name from users where age > 18")
    assert r['selected_columns'] == ['name']
    assert r['table_name'] == 'users'
    assert r['where_conditions'] == ['age > 18']

    # 带分号
    r = parse_sql("SELECT * FROM t WHERE x = 1;")
    assert r['selected_columns'] == ['*']
    assert r['table_name'] == 't'
    assert r['where_conditions'] == ['x = 1']

    # 非法输入
    try:
        parse_
```

### qwen3.8-27b-nvfp4 - HTTP Downloader

```python
```python
import asyncio
import time
import aiohttp


async def download_one(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff: float = 1.0,
) -> dict:
    async with semaphore:
        last_exc = None
        for attempt in range(1, max_retries + 1):
            start = time.perf_counter()
            try:
                async with asyncio.wait_for(
                    session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)),
                    timeout=timeout,
                ) as resp:
                    body = await resp.read()
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    return {
                        "url": url,
                        "status": resp.status,
                        "size": len(body),
                        "elapsed_ms": round(elapsed_ms, 2),
                    }
            except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as e:
                last_exc = e
                if attempt < max_retries:
                    await asyncio.sleep(backoff * (2 ** (attempt - 1)))
        # 所有重试耗尽
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "url": url,
            "status": -1,
            "size": 0,
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(last_exc),
        }


async def concurrent_download(
    urls: list[str],
    concurrency: int = 10,
    timeout: float = 10.0,
    max_retries: int = 3,
) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            download_one(session, url, semaphore, timeout, max_retries)
            for url in urls
        ]
        results = await asyncio.gather(*tasks)
    return results


# ── 使用示例 ────────────────────────────────────
```
