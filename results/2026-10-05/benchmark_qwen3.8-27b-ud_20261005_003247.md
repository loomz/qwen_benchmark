# Qwen 编码能力 & 效率基准测试 (qwen3.8-27b, profile=qwen3.8-27b-ud)

时间: 2026-10-05 00:46:18
硬件: RTX 5090D 24G
服务端: model-proxy @ http://localhost:5807/v1/messages -> llama-swap :8080 -> llama-server :5803
每任务运行: 3 次
reasoning_effort: xhigh  |  max_tokens: 16384

## 0. 当前 llama-server 配置 (qwen3.8-27b, profile=qwen3.8-27b-ud, 原样记录)

**进程** (PID 111855, port 5803):

```bash
/home/loomz/.llama.cpp/llama.cpp/build/bin/llama-server
  -m /home/loomz/.llama.cpp/models/Qwen3.8-27B-UD-Q4_K_XL.gguf
  --log-file /home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log
  --host 0.0.0.0
  --port 5803
  -c 128000
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
    "n_ctx": 128000
  },
  "total_slots": 1,
  "model_alias": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-UD-Q4_K_XL.gguf",
  "model_ftype": "Q4_K - Medium",
  "model_path": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-UD-Q4_K_XL.gguf",
  "modalities": {
    "vision": false,
    "video": false,
    "audio": false
  },
  "media_marker": "<__media_jXSlpdAhaLEQzmLimy7D6CEPSifSH85O__>",
  "endpoint_slots": true,
  "endpoint_props": false,
  "endpoint_metrics": false,
  "ui": true,
  "ui_settings": {},
  "chat_template": "{%- set image_count = namespace(value=0) %}\n{%- set video_count = namespace(value=0) %}\n{%- macro render_content(content, do_vision_count, is_system_content=false) %}\n    {%- if content is string %}\n        {{- content }}\n    {%- elif content is iterable and content is not mapping %}\n        {%- for item in content %}\n            {%- if 'image' in item or 'image_url' in item or item.type == 'image' %}\n                {%- if is_system_content %}\n                    {{- raise_exception('System message cannot contain images.') }}\n                {%- endif %}\n                {%- if do_vision_count %}\n                    {%- set image_count.value = image_count.value + 1 %}\n                {%- endif %}\n                {%- if add_vision_id %}\n                    {{- 'Picture ' ~ image_count.value ~ ': ' }}\n                {%- endif %}\n                {{- '<|vision_start|><|image_pad|><|vision_end|>' }}\n            {%- elif 'video' in item or item.type == 'video' %}\n                {%- if is_system_content %}\n                    {{- raise_exception('System message cannot contain videos.') }}\n                {%- endif %}\n                {%- if do_vision_count %}\n                    {%- set video_count.value = video_count.value + 1 %}\n                {%- endif %}\n                {%- if add_vision_id %}\n                    {{- 'Video ' ~ video_count.value ~ ': ' }}\n                {%- endif %}\n                {{- '<|vision_start|><|video_pad|><|vision_end|>' }}\n            {%- elif 'text' in item %}\n                {{- item.text }}\n            {%- else %}\n                {{- raise_exception('Unexpected item type in content.') }}\n            {%- endif %}\n        {%- endfor %}\n    {%- elif content is none or content is undefined %}\n        {{- '' }}\n    {%- else %}\n        {{- raise_exception('Unexpected content type.') }}\n    {%- endif %}\n{%- endmacro %}\n{%- if not messages %}\n    {{- raise_exception('No messages provided.') }}\n{%- endif %}\n{%- set sysns = namespace(count=0, text='') %}\n{%- for message in messages %}\n    {%- if message.role == 'system' or message.role == 'developer' %}  {# tolerant: collect system msgs anywhere #}\n        {%- set sys_content = render_content(message.content, false, true)|trim %}\n        {%- if sys_content %}\n            {%- set sysns.text = sysns.text + ('\\n' if sysns.text else '') + sys_content %}\n        {%- endif %}\n        {%- set sysns.count = sysns.count + 1 %}\n    {%- endif %}\n{%- endfor %}\n{%- set num_sys = sysns.count %}\n{%- set merged_system = sysns.text %}\n{%- set reasoning_instructions = '' %}\n{%- if enable_thinking is undefined or enable_thinking is true %}\n    {%- set resolved_reasoning_effort = reasoning_effort|default('xhigh') %}\n    {%- if resolved_reasoning_effort == 'high' %}\n        {%- set resolved_reasoning_effort = 'xhigh' %}\n    {%- endif %}\n    {%- if resolved_reasoning_effort not in ('xhigh', 'medium', 'low') %}\n        {{- raise_exception('Unexpected reasoning effort ' ~ reasoning_effort ~ '. Supported types are xhigh (default), medium, and low.') }}\n    {%- endif %}\n    {%- if resolved_reasoning_effort == 'xhigh' %}\n        {%- set reasoning_instructions = 'Reasoning effort is set to xhigh. Please think carefully through the task, validate key assumptions, consider plausible alternatives, and prioritize correctness, consistency, and clarity in the final answer.' %}\n    {%- elif resolved_reasoning_effort == 'low' %}\n        {%- set reasoning_instructions = 'Reasoning effort is set to low. Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.' %}\n    {%- endif %}\n{%- endif %}\n{%- if tools and tools is iterable and tools is not mapping %}\n    {{- '<|im_start|>system\\n' }}\n    {%- if reasoning_instructions %}\n        {{- reasoning_instructions + '\\n\\n' }}\n    {%- endif %}\n    {{- \"# Tools\\n\\nYou have access to the following functions:\\n\\n<tools>\" }}\n    {%- for tool in tools %}\n        {{- \"\\n\" }}\n        {{- tool | tojson }}\n    {%- endfor %}\n    {{- \"\\n</tools>\" }}\n    {{- '\\n\\nIf you choose to call a function ONLY reply in the following format with NO suffix:\\n\\n<tool_call>\\n<function=example_function_name>\\n<parameter=example_parameter_1>\\nvalue_1\\n</parameter>\\n<parameter=example_parameter_2>\\nThis is the value for the second parameter\\nthat can span\\nmultiple lines\\n</parameter>\\n</function>\\n</tool_call>\\n\\n<IMPORTANT>\\nReminder:\\n- Function calls MUST follow the specified format: an inner <function=...></function> block must be nested within <tool_call></tool_call> XML tags\\n- Required parameters MUST be specified\\n- You may provide optional reasoning for your function call in natural language BEFORE the function call, but NOT after\\n- If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls\\n</IMPORTANT>' }}\n    {%- if merged_system %}\n        {{- '\\n\\n' + merged_system }}\n    {%- endif %}\n    {{- '<|im_end|>\\n' }}\n{%- else %}\n    {%- if merged_system %}\n        {{- '<|im_start|>system\\n' + (reasoning_instructions + '\\n\\n' if reasoning_instructions else '')  + merged_system + '<|im_end|>\\n' }}\n    {%- elif reasoning_instructions %}\n        {{- '<|im_start|>system\\n' + reasoning_instructions + '<|im_end|>\\n' }}\n    {%- endif %}\n{%- endif %}\n{%- set ns = namespace(multi_step_tool=true, last_query_index=messages|length - 1) %}\n{%- for message in messages[::-1] %}\n    {%- set index = (messages|length - 1) - loop.index0 %}\n    {%- if ns.multi_step_tool and message.role == \"user\" %}\n        {%- set content = render_content(message.content, false)|trim %}\n        {%- if not(content.startswith('<tool_response>') and content.endswith('</tool_response>')) %}\n            {%- set ns.multi_step_tool = false %}\n            {%- set ns.last_query_index = index %}\n        {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- for message in messages %}\n    {%- if message.role != \"system\" and message.role != \"developer\" %}  {# tolerant: system msgs merged above, skip here #}\n    {%- set content = render_content(message.content, true)|trim %}\n    {%- if message.role == \"user\" %}\n        {{- '<|im_start|>' + message.role + '\\n' + content + '<|im_end|>' + '\\n' }}\n    {%- elif message.role == \"assistant\" %}\n        {%- set reasoning_content = '' %}\n        {%- if message.reasoning_content is string %}\n            {%- set reasoning_content = message.reasoning_content %}\n        {%- endif %}\n        {%- set reasoning_content = reasoning_content|trim %}\n        {%- if preserve_thinking is undefined or preserve_thinking is true or loop.index0 > ns.last_query_index %}\n            {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content + '\\n</think>\\n\\n' + content }}\n        {%- else %}\n            {{- '<|im_start|>' + message.role + '\\n' + content }}\n        {%- endif %}\n        {%- if message.tool_calls and message.tool_calls is iterable and message.tool_calls is not mapping %}\n            {%- for tool_call in message.tool_calls %}\n                {%- if tool_call.function is defined %}\n                    {%- set tool_call = tool_call.function %}\n                {%- endif %}\n                {%- if tool_call.name is not defined or tool_call.name is none %}\n                    {{- raise_exception('Tool call is missing a function name.') }}\n                {%- endif %}\n                {%- if loop.first %}\n                    {%- if content|trim %}\n                        {{- '\\n\\n<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                    {%- else %}\n                        {{- '<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                    {%- endif %}\n                {%- else %}\n                    {{- '\\n<tool_call>\\n<function=' + tool_call.name + '>\\n' }}\n                {%- endif %}\n                {%- if tool_call.arguments is mapping %}\n                    {%- for args_name, args_value in tool_call.arguments|items %}\n                        {{- '<parameter=' + args_name + '>\\n' }}\n                        {%- set args_value = args_value | string if args_value is string else args_value | tojson | safe %}\n                        {{- args_value }}\n                        {{- '\\n</parameter>\\n' }}\n                    {%- endfor %}\n                {%- elif tool_call.arguments is string %}\n                    {%- if tool_call.arguments|trim %}\n                        {{- raise_exception('Tool call arguments for function \"' + (tool_call.name | string) + '\" were passed as a JSON string. Parse them into an object before calling apply_chat_template.') }}\n                    {%- endif %}\n                {%- elif tool_call.arguments is defined and tool_call.arguments is not none %}\n                    {{- raise_exception('Tool call arguments for function \"' + (tool_call.name | string) + '\" must be an object/mapping or a JSON string.') }}\n                {%- endif %}\n                {{- '</function>\\n</tool_call>' }}\n            {%- endfor %}\n        {%- endif %}\n        {{- '<|im_end|>\\n' }}\n    {%- elif message.role == \"tool\" %}\n        {%- if loop.previtem and loop.previtem.role != \"tool\" %}\n            {{- '<|im_start|>user' }}\n        {%- endif %}\n        {{- '\\n<tool_response>\\n' }}\n        {{- content }}\n        {{- '\\n</tool_response>' }}\n        {%- if not loop.last and loop.nextitem.role != \"tool\" %}\n            {{- '<|im_end|>\\n' }}\n        {%- elif loop.last %}\n            {{- '<|im_end|>\\n' }}\n        {%- endif %}\n    {%- else %}\n        {{- raise_exception('Unexpected message role.') }}\n    {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- if add_generation_prompt %}\n    {{- '<|im_start|>assistant\\n' }}\n    {%- if enable_thinking is defined and enable_thinking is false %}\n        {{- '<think>\\n\\n</think>\\n\\n' }}\n    {%- else %}\n        {{- '<think>\\n' }}\n    {%- endif %}\n{%- endif %}\n{#- Unsloth fixes - developer role, merged system messages, tool calling #}",
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

## qwen3.8-27b

| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) | 推理词数(估) | 代码词数(估) | 总Tok | 生成Tok/s* | 通过 |
|------|---|-------------|-------------|----------|---------|---------|-------|-------------|------|
| Fibonacci Memoization | 1 | 0.25 | 6.22 | 7.08 | 407 | 68 | 923 | 135.1 | Y |
| Fibonacci Memoization | 2 | 0.10 | 24.28 | 25.12 | 1598 | 68 | 2994 | 119.6 | Y |
| Fibonacci Memoization | 3 | 0.10 | 24.49 | 25.33 | 1572 | 68 | 2956 | 117.2 | Y |
| LRU Cache | 1 | 0.18 | 39.53 | 42.88 | 2436 | 192 | 5596 | 131.0 | Y |
| LRU Cache | 2 | 0.10 | 49.93 | 53.86 | 3095 | 230 | 7084 | 131.8 | Y |
| LRU Cache | 3 | 0.09 | 23.93 | 28.95 | 1457 | 319 | 4263 | 147.7 | Y |
| Async Task Queue | 1 | 0.20 | 118.45 | 127.23 | 6913 | 485 | 15609 | 122.9 | - |
| Async Task Queue | 2 | 0.10 | 105.22 | 111.94 | 6440 | 439 | 13135 | 117.4 | - |
| Async Task Queue | 3 | 0.09 | 77.57 | 85.22 | 4765 | 499 | 10953 | 128.7 | - |
| SQL Parser | 1 | 0.17 | 20.29 | 24.09 | 1151 | 218 | 3163 | 132.3 | Y |
| SQL Parser | 2 | 0.10 | 108.39 | 114.33 | 6626 | 344 | 13455 | 117.8 | Y |
| SQL Parser | 3 | 0.10 | 34.38 | 38.18 | 2074 | 247 | 4651 | 122.1 | Y |
| HTTP Downloader | 1 | 0.20 | 6.80 | 9.73 | 453 | 184 | 1538 | 161.4 | - |
| HTTP Downloader | 2 | 0.13 | 14.95 | 18.55 | 657 | 221 | 2754 | 149.5 | - |
| HTTP Downloader | 3 | 0.10 | 87.41 | 90.45 | 5292 | 189 | 10681 | 118.2 | - |

**均值**: TTFT推理=0.13s, TTFT代码=49.46s, 总耗时=53.53s, 推理词数(估)=2996, 代码词数(估)=251, 服务端Tok/s=130.2, PromptTok/s=153.9, 通过率=9/9 (仅verify任务)

## 对比总结

| 指标 | qwen3.8-27b |
|------|-------|
| 首字延迟-推理 (s) | 0.13 |
| 首字延迟-代码 (s) | 49.46 |
| 总耗时 (s) | 53.53 |
| 生成速度 (tok/s)* | 130.2 |
| Prompt 速度 (tok/s)* | 153.9 |
| 推理词数(估) | 2996 |
| 代码词数(估) | 251 |
| 代码通过率(仅verify) | 100% (9/9) |

## 代码输出样例

### qwen3.8-27b - Fibonacci Memoization
**执行: PASS**

```python
from functools import wraps

def memoize(func):
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper

@memoize
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(20) == 6765
```

### qwen3.8-27b - LRU Cache
**执行: PASS**

```python
from __future__ import annotations

import threading
import unittest
from collections import OrderedDict
from typing import Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._capacity: int = capacity
        self._cache: OrderedDict[K, V] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: K, value: V) -> None:
        with self._lock:
            if self._capacity == 0:
                return
            if key in self._cache:
                self._cache[key] = value
                self._cache.move_to_end(key)
                return
            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)
            self._cache[key] = value

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._cache


class LRUCacheTests(unittest.TestCase):
    def test_basic_get_and_put(self) -> None:
        cache: LRUCache[int, str] = LRUCache(2)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.get(1), "a")
        self.assertIsNone(cache.get(3))

    def test_lru_eviction(self) -> None:
        cache: LRUCache[int, int] = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.put(3, 3)
        self.assertIsNone(cache.get(1))
        self.assertEqual(cache.get(2), 2)
        self.assertEqual(cache.get(3), 3)

    def test_update_existing_key(self) -> None:
        cache: LRUCache[str, int] = LRUCache
```

### qwen3.8-27b - Async Task Queue

```python
import asyncio
import heapq
import itertools
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple


@dataclass
class Task:
    id: int
    priority: int
    coro_factory: Callable[..., Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    retries: int = 0
    available_at: float = 0.0


class AsyncPriorityTaskQueue:
    def __init__(
        self,
        max_concurrency: int = 4,
        retry_base_delay: float = 0.1,
        max_retries: int = 3,
    ):
        if max_concurrency < 1:
            raise ValueError("max_concurrency 必须大于 0")
        if max_retries < 0:
            raise ValueError("max_retries 不能小于 0")

        self.max_concurrency = max_concurrency
        self.retry_base_delay = retry_base_delay
        self.max_retries = max_retries

        self._ready = []
        self._delayed = []
        self._seq = itertools.count()

        self._ready_event = asyncio.Event()
        self._delayed_event = asyncio.Event()

        self._workers = []
        self._scheduler = None
        self._closed = False
        self._pending = 0

        self.stats = {
            "completed": 0,
            "failed": 0,
            "retries": 0,
        }

    async def start(self):
        if self._workers:
            return

        self._closed = False
        self._scheduler = asyncio.create_task(
            self._scheduler_loop(),
            name="task-queue-scheduler",
        )
        self._workers = [
            asyncio.create_task(self._worker_loop(), name=f"task-worker-{i}")
            for i in range(self.max_concurrency)
        ]

    def add_task(
        self,
        coro_factory: Callable[..., Any],
        priority: int = 0,
        *args: Any,
        **kwargs: Any,
    ) -> int:
        if self._closed:
            raise RuntimeError("队列已关闭")

        task_id = next(self._seq)
        task = Task(task_id, priority, coro_factory, args, kwargs)

        heapq.heappush(self._ready, (priority, task_id, task))
    
```

### qwen3.8-27b - SQL Parser
**执行: PASS**

```python
import re
import unittest


class SimpleSQLParser:
    _SELECT_RE = re.compile(
        r"""
        ^\s*
        SELECT\s+
        (?P<columns>.+?)\s+
        FROM\s+
        (?P<table>[\w.]+)
        (?:\s+WHERE\s+(?P<conditions>.+?))?\s*
        ;?\s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )
    _AND_RE = re.compile(r"\s+AND\s+", re.IGNORECASE)

    def parse(self, sql: str) -> dict:
        if not isinstance(sql, str):
            raise TypeError("sql must be a string")

        match = self._SELECT_RE.match(sql)
        if not match:
            raise ValueError(f"Cannot parse SQL: {sql!r}")

        selected_columns = [
            column.strip()
            for column in match.group("columns").split(",")
            if column.strip()
        ]

        table_name = match.group("table")

        conditions = match.group("conditions")
        where_conditions = (
            [condition.strip() for condition in self._AND_RE.split(conditions) if condition.strip()]
            if conditions
            else []
        )

        return {
            "selected_columns": selected_columns,
            "table_name": table_name,
            "where_conditions": where_conditions,
        }


def parse_sql(sql: str) -> dict:
    return SimpleSQLParser().parse(sql)


class TestSimpleSQLParser(unittest.TestCase):
    def test_single_column_and_single_condition(self):
        result = parse_sql("SELECT name FROM users WHERE age > 18")

        self.assertEqual(
            result,
            {
                "selected_columns": ["name"],
                "table_name": "users",
                "where_conditions": ["age > 18"],
            },
        )

    def test_multiple_columns_and_multiple_conditions(self):
        result = parse_sql("SELECT id, name, email FROM users WHERE age >= 18 AND active = 1")

        self.assertEqual(
            result,
            {
                "selected_columns": ["id", "name", "email"],
                "table_name": "user
```

### qwen3.8-27b - HTTP Downloader

```python
```python
import asyncio
import time

import aiohttp


async def download_one(
    url: str,
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    timeout: float = 10.0,
    retries: int = 3,
    backoff: float = 0.5,
) -> dict:
    start = time.perf_counter()
    last_exc = None

    async with sem:
        for attempt in range(1, retries + 1):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True,
                ) as resp:
                    data = await resp.read()
                    return {
                        "url": url,
                        "status": resp.status,
                        "size": len(data),
                        "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
                    }
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                last_exc = exc
                if attempt < retries:
                    await asyncio.sleep(backoff * attempt)

    return {
        "url": url,
        "status": None,
        "size": 0,
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
        "error": str(last_exc),
    }


async def download_all(
    urls: list,
    concurrency: int = 10,
    timeout: float = 10.0,
    retries: int = 3,
) -> list:
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": "async-downloader/1.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [
            download_one(u, session, sem, timeout=timeout, retries=retries)
            for u in urls
        ]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    urls = [
        "https://httpbin.org/status/200",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/500",
        "https://example.com",
    ]
    results = asyncio.run(download_all(urls, concurren
```
