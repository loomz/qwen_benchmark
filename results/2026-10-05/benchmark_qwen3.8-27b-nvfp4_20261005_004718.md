# Qwen 编码能力 & 效率基准测试 (qwen3.8-27b, profile=qwen3.8-27b-nvfp4)

时间: 2026-10-05 01:02:53
硬件: RTX 5090D 24G
服务端: model-proxy @ http://localhost:5807/v1/messages -> llama-swap :8080 -> llama-server :5804
每任务运行: 3 次
reasoning_effort: xhigh  |  max_tokens: 16384

## 0. 当前 llama-server 配置 (qwen3.8-27b, profile=qwen3.8-27b-nvfp4, 原样记录)

**进程** (PID 122953, port 5804):

```bash
/home/loomz/.llama.cpp/llama.cpp/build/bin/llama-server
  -m /home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf
  --log-file /home/loomz/.llama.cpp/logs/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf.log
  --host 0.0.0.0
  --port 5804
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
  "model_alias": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
  "model_ftype": "Q8_0",
  "model_path": "/home/loomz/.llama.cpp/models/Qwen3.8-27B-NVFP4-MTP-MID-HIGH.gguf",
  "modalities": {
    "vision": false,
    "video": false,
    "audio": false
  },
  "media_marker": "<__media_uxXJrWFieK7OR3ibqDDCHGf9vUkNUOre__>",
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
| Fibonacci Memoization | 1 | 0.24 | 23.57 | 24.48 | 1512 | 74 | 2965 | 122.3 | Y |
| Fibonacci Memoization | 2 | 0.10 | 60.94 | 61.85 | 4198 | 74 | 7567 | 122.5 | Y |
| Fibonacci Memoization | 3 | 0.10 | 19.03 | 19.84 | 1292 | 68 | 2488 | 126.0 | Y |
| LRU Cache | 1 | 0.17 | 29.69 | 33.19 | 1887 | 232 | 4398 | 133.2 | N(Traceback (most ) |
| LRU Cache | 2 | 0.10 | 20.49 | 23.67 | 1340 | 214 | 3305 | 140.2 | Y |
| LRU Cache | 3 | 0.09 | 17.77 | 21.25 | 1143 | 232 | 3080 | 145.6 | Y |
| Async Task Queue | 1 | 0.19 | 87.84 | 95.86 | 5491 | 519 | 12124 | 126.7 | - |
| Async Task Queue | 2 | 0.12 | 81.29 | 88.63 | 5040 | 477 | 10714 | 121.1 | - |
| Async Task Queue | 3 | 0.12 | 140.28 | 140.28 | 8845 | 0 | 16384 | 116.9 | - |
| SQL Parser | 1 | 0.18 | 110.82 | 116.69 | 6459 | 347 | 13798 | 118.4 | Y |
| SQL Parser | 2 | 0.11 | 28.96 | 32.11 | 1690 | 187 | 3904 | 122.0 | Y |
| SQL Parser | 3 | 0.10 | 68.24 | 71.85 | 4273 | 214 | 8569 | 119.4 | Y |
| HTTP Downloader | 1 | 0.18 | 127.46 | 127.46 | 7887 | 0 | 16384 | 128.7 | - |
| HTTP Downloader | 2 | 0.10 | 36.01 | 38.65 | 2208 | 186 | 4882 | 126.6 | - |
| HTTP Downloader | 3 | 0.09 | 27.33 | 30.03 | 1635 | 176 | 3948 | 131.9 | - |

**均值**: TTFT推理=0.13s, TTFT代码=58.65s, 总耗时=61.72s, 推理词数(估)=3660, 代码词数(估)=200, 服务端Tok/s=126.8, PromptTok/s=157.0, 通过率=8/9 (仅verify任务)

## 对比总结

| 指标 | qwen3.8-27b |
|------|-------|
| 首字延迟-推理 (s) | 0.13 |
| 首字延迟-代码 (s) | 58.65 |
| 总耗时 (s) | 61.72 |
| 生成速度 (tok/s)* | 126.8 |
| Prompt 速度 (tok/s)* | 157.0 |
| 推理词数(估) | 3660 |
| 代码词数(估) | 200 |
| 代码通过率(仅verify) | 89% (8/9) |

## 代码输出样例

### qwen3.8-27b - Fibonacci Memoization
**执行: PASS**

```python
from functools import wraps

def memoize(func):
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items(), key=lambda item: item[0])))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache
    return wrapper

@memoize
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(20) == 6765
```

### qwen3.8-27b - LRU Cache
**执行: Traceback (most recent call last):
  File "<string>", line 95, in <module>
  File "<string>", line 55, in test_basic_eviction
AssertionError**

```python
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Generic, List, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")

        self._capacity: int = capacity
        self._data: "OrderedDict[K, V]" = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key not in self._data:
                return None

            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._data:
                self._data[key] = value
                self._data.move_to_end(key)
            else:
                self._data[key] = value

                if len(self._data) > self._capacity:
                    self._data.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


def test_basic_eviction() -> None:
    cache: LRUCache[str, int] = LRUCache[str, int](2)

    cache.put("a", 1)
    cache.put("b", 2)

    assert cache.get("a") == 1

    cache.put("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") is None
    assert cache.get("c") == 3


def test_update_existing_key() -> None:
    cache: LRUCache[str, int] = LRUCache[str, int](2)

    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)
    cache.put("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") == 10
    assert cache.get("c") == 3


def test_thread_safety() -> None:
    cache: LRUCache[int, int] = LRUCache[int, int](100)

    def worker(start: int) -> None:
        for i in range(start, start + 1000):
            cache.put(i % 100, i)
            cache.get(i % 100)

    threads: List[threading.Thread] = [
   
```

### qwen3.8-27b - Async Task Queue

```python
import asyncio
import heapq
import inspect
import itertools
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: int
    priority: int
    func: Callable[[], Any]
    attempts: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None


class AsyncTaskQueue:
    def __init__(
        self,
        concurrency: int = 4,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 10.0,
    ):
        self.concurrency = max(1, int(concurrency))
        self.max_retries = max(0, int(max_retries))
        self.base_delay = float(base_delay)
        self.max_delay = float(max_delay)

        self._heap: List[tuple] = []
        self._counter = itertools.count()
        self._cv: Optional[asyncio.Condition] = None
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._active = 0

        self._completed = 0
        self._failed = 0
        self._retries = 0

        self._tasks: Dict[int, Task] = {}

    async def _ensure_cv(self) -> None:
        if self._cv is None:
            self._cv = asyncio.Condition()

    async def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: int = 0,
        **kwargs: Any,
    ) -> Task:
        await self._ensure_cv()

        task_id = next(self._counter)
        task = Task(
            id=task_id,
            priority=priority,
            func=lambda: func(*args, **kwargs),
        )
        self._tasks[task_id] = task

        async with self._cv:
            heapq.heappush(self._heap, (priority, task_id, task))
            self._cv.notify_all()

        return task

    async def start(self) -> None:
        await self._ensure_cv()
        if self._running:
   
```

### qwen3.8-27b - SQL Parser
**执行: PASS**

```python
import re
import unittest

_SQL_RE = re.compile(
    r'^\s*SELECT\s+(?P<columns>.+?)\s+FROM\s+'
    r'(?P<table>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)'
    r'\s*(?:WHERE\s+(?P<where>.+?))?\s*;?\s*$',
    re.IGNORECASE | re.DOTALL
)


def _split_columns(columns):
    parts = []
    current = []
    depth = 0
    in_single = False
    in_double = False

    for ch in columns:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double

        if not in_single and not in_double:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                part = ''.join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue

        current.append(ch)

    part = ''.join(current).strip()
    if part:
        parts.append(part)

    return parts


def _split_conditions(where):
    pattern = re.compile(r'\b(?:AND|OR)\b', re.IGNORECASE)
    parts = []
    last = 0

    for m in pattern.finditer(where):
        prefix = where[:m.start()]
        depth = prefix.count('(') - prefix.count(')')
        if depth == 0 and prefix.count("'") % 2 == 0 and prefix.count('"') % 2 == 0:
            part = where[last:m.start()].strip()
            if part:
                parts.append(part)
            last = m.end()

    part = where[last:].strip()
    if part:
        parts.append(part)

    return parts


def parse_sql(sql):
    if not isinstance(sql, str):
        raise ValueError("SQL must be a string")

    sql = sql.strip()
    if not sql:
        raise ValueError("SQL is empty")

    m = _SQL_RE.match(sql)
    if not m:
        raise ValueError("Unsupported SQL")

    selected_columns = _split_columns(m.group('columns'))
    table_name = m.group('table').strip()
    where = m.group('where')
    where_c
```

### qwen3.8-27b - HTTP Downloader

```python

```
