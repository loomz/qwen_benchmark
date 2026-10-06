# Qwen 编码能力 & 效率基准测试 (qwen3.8-27b-ud, profile=qwen3.8-27b-ud)

时间: 2026-10-06 04:40:50
硬件: RTX 5090D 24G
服务端: llama-swap @ http://localhost:8080/v1/chat/completions -> llama-server :5806
每任务运行: 3 次
reasoning_effort: medium  |  max_tokens: 16384

## 0. 当前 llama-server 配置 (qwen3.8-27b-ud, profile=qwen3.8-27b-ud, 原样记录)

**进程** (PID 51421, port 5806):

```bash
/home/loomz/.llama.cpp/llama.cpp/build/bin/llama-server
  -m /home/loomz/.llama.cpp/models/Qwen3.8-27B-UD-Q4_K_XL.gguf
  --log-file /home/loomz/.llama.cpp/logs/Qwen3.8-27B-UD-Q4_K_XL.log
  --host 0.0.0.0
  --port 5806
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
  "media_marker": "<__media_QDoOOhJAkypYg3cnEhYvg05FdYDTS9Kx__>",
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

## qwen3.8-27b-ud

| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) | 推理词数(估) | 代码词数(估) | 总Tok | 生成Tok/s* | 通过 |
|------|---|-------------|-------------|----------|---------|---------|-------|-------------|------|
| Fibonacci Memoization | 1 | 0.19 | 2.33 | 3.19 | 175 | 70 | 516 | 172.0 | Y |
| Fibonacci Memoization | 2 | 0.07 | 1.93 | 2.72 | 151 | 61 | 451 | 170.0 | Y |
| Fibonacci Memoization | 3 | 0.07 | 2.79 | 3.65 | 159 | 70 | 610 | 170.5 | Y |
| LRU Cache | 1 | 0.15 | 4.79 | 11.19 | 258 | 386 | 1879 | 170.2 | Y |
| LRU Cache | 2 | 0.07 | 1.44 | 6.34 | 60 | 286 | 1042 | 166.4 | N(Traceback (most ) |
| LRU Cache | 3 | 0.07 | 4.72 | 11.11 | 261 | 396 | 1874 | 169.8 | Y |
| Async Task Queue | 1 | 0.15 | 17.79 | 25.13 | 1187 | 366 | 3770 | 150.9 | - |
| Async Task Queue | 2 | 0.07 | 15.71 | 23.97 | 1098 | 436 | 3528 | 147.6 | - |
| Async Task Queue | 3 | 0.07 | 10.92 | 19.51 | 716 | 425 | 2873 | 147.8 | - |
| SQL Parser | 1 | 0.14 | 6.36 | 10.42 | 320 | 217 | 1746 | 169.8 | Y |
| SQL Parser | 2 | 0.07 | 7.83 | 12.36 | 373 | 258 | 1995 | 162.3 | Y |
| SQL Parser | 3 | 0.07 | 2.69 | 7.37 | 112 | 242 | 1218 | 166.7 | Y |
| HTTP Downloader | 1 | 0.15 | 1.25 | 5.38 | 91 | 226 | 839 | 160.4 | - |
| HTTP Downloader | 2 | 0.07 | 1.10 | 5.18 | 87 | 229 | 812 | 158.9 | - |
| HTTP Downloader | 3 | 0.07 | 1.26 | 5.45 | 92 | 227 | 848 | 157.6 | - |

**均值**: TTFT推理=0.10s, TTFT代码=5.53s, 总耗时=10.20s, 推理词数(估)=343, 代码词数(估)=260, 服务端Tok/s=162.7, PromptTok/s=1141.3, 通过率=8/9 (仅verify任务)

## 对比总结

| 指标 | qwen3.8-27b-ud |
|------|-------|
| 首字延迟-推理 (s) | 0.10 |
| 首字延迟-代码 (s) | 5.53 |
| 总耗时 (s) | 10.20 |
| 生成速度 (tok/s)* | 162.7 |
| Prompt 速度 (tok/s)* | 1141.3 |
| 推理词数(估) | 343 |
| 代码词数(估) | 260 |
| 代码通过率(仅verify) | 89% (8/9) |

## 代码输出样例

### qwen3.8-27b-ud - Fibonacci Memoization
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
```

### qwen3.8-27b-ud - LRU Cache
**执行: PASS**

```python
```python
from __future__ import annotations

import threading
from typing import Any, Hashable, Optional


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: Hashable, value: Any) -> None:
        self.key: Hashable = key
        self.value: Any = value
        self.prev: Optional[_Node] = None
        self.next: Optional[_Node] = None


class LRUCache:
    """Thread-safe LRU Cache with O(1) get/put."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity: int = capacity
        self._map: dict[Hashable, _Node] = {}
        self._lock: threading.Lock = threading.Lock()
        self._head: _Node = _Node(None, None)
        self._tail: _Node = _Node(None, None)
        self._head.next = self._tail
        self._tail.prev = self._head

    # ---------- internal helpers (caller must hold lock) ----------

    def _remove(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_front(self, node: _Node) -> None:
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    # ---------- public API ----------

    def get(self, key: Hashable) -> Optional[Any]:
        with self._lock:
            node = self._map.get(key)
            if node is None:
                return None
            self._remove(node)
            self._add_to_front(node)
            return node.value

    def put(self, key: Hashable, value: Any) -> None:
        with self._lock:
            node = self._map.get(key)
            if node is not None:
                node.value = value
                self._remove(node)
                self._add_to_front(node)
            else:
                new_node = _Node(key, value)
                self._map[key] = new_node
                self._add_to_front(new_node)
                if len(
```

### qwen3.8-27b-ud - Async Task Queue

```python
```python
import asyncio
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Coroutine


@dataclass(order=True)
class Task:
    priority: int
    id: int = field(compare=False)
    coro: Any = field(compare=False)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)


class AsyncTaskQueue:
    def __init__(self, concurrency: int = 5, base_delay: float = 0.5):
        self._heap: list[Task] = []
        self._lock = asyncio.Lock()
        self._concurrency = concurrency
        self._base_delay = base_delay
        self._id_counter = 0
        self._pending = 0
        self._stats = {"completed": 0, "failed": 0, "retries": 0}

    def submit(self, coro: Coroutine, priority: int = 0) -> int:
        self._id_counter += 1
        task = Task(priority=priority, id=self._id_counter, coro=coro)
        heapq.heappush(self._heap, task)
        self._pending += 1
        return self._id_counter

    async def _worker(self) -> None:
        while True:
            async with self._lock:
                if not self._heap:
                    await asyncio.sleep(0.01)
                    continue
                task = heapq.heappop(self._heap)

            try:
                await task.coro
                self._stats["completed"] += 1
                self._pending -= 1
            except Exception:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    self._stats["retries"] += 1
                    delay = self._base_delay * (2 ** task.retry_count)
                    print(f"  [retry] task#{task.id} attempt {task.retry_count}, "
                          f"backoff {delay:.2f}s")
                    await asyncio.sleep(delay)
                    async with self._lock:
                        heapq.heappush(self._heap, task)
                else:
                    self._stats["failed"] += 1
                    self.
```

### qwen3.8-27b-ud - SQL Parser
**执行: PASS**

```python
```python
import re
import unittest


def parse_sql(sql: str) -> dict:
    sql = sql.strip().rstrip(';')
    pattern = r'^\s*SELECT\s+(.+?)\s+FROM\s+(\w+)\s*(?:WHERE\s+(.+?))?\s*$'
    match = re.match(pattern, sql, re.IGNORECASE)
    if not match:
        raise ValueError(f"无法解析 SQL: {sql}")

    selected_columns = [c.strip() for c in match.group(1).split(',')]
    table_name = match.group(2)

    where_conditions = []
    if match.group(3):
        where_conditions = [
            c.strip() for c in re.split(r'\s+AND\s+', match.group(3), flags=re.IGNORECASE)
        ]

    return {
        'selected_columns': selected_columns,
        'table_name': table_name,
        'where_conditions': where_conditions,
    }


class TestSQLParser(unittest.TestCase):
    def test_single_column_no_where(self):
        r = parse_sql("SELECT name FROM users")
        self.assertEqual(r['selected_columns'], ['name'])
        self.assertEqual(r['table_name'], 'users')
        self.assertEqual(r['where_conditions'], [])

    def test_multiple_columns(self):
        r = parse_sql("SELECT id, name, age FROM users")
        self.assertEqual(r['selected_columns'], ['id', 'name', 'age'])
        self.assertEqual(r['table_name'], 'users')
        self.assertEqual(r['where_conditions'], [])

    def test_star(self):
        r = parse_sql("SELECT * FROM products")
        self.assertEqual(r['selected_columns'], ['*'])
        self.assertEqual(r['table_name'], 'products')

    def test_single_where(self):
        r = parse_sql("SELECT name FROM users WHERE age > 18")
        self.assertEqual(r['selected_columns'], ['name'])
        self.assertEqual(r['table_name'], 'users')
        self.assertEqual(r['where_conditions'], ['age > 18'])

    def test_multiple_where_and(self):
        r = parse_sql("SELECT id FROM orders WHERE status = 'active' AND amount > 100")
        self.assertEqual(r['selected_columns'], ['id'])
        self.assertEqual(r['table_name'], 'orders')
        self.assertEqual(r[
```

### qwen3.8-27b-ud - HTTP Downloader

```python
```python
import asyncio
import time
import aiohttp
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DownloadResult:
    url: str
    status: int
    size: int
    elapsed_ms: float


async def _download_one(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff: float = 0.5,
) -> DownloadResult:
    last_status = 0
    last_size = 0

    for attempt in range(max_retries):
        start = time.perf_counter()
        try:
            async with semaphore:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    data = await resp.read()
                    last_status = resp.status
                    last_size = len(data)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    return DownloadResult(url=url, status=last_status, size=last_size, elapsed_ms=round(elapsed_ms, 2))
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            last_status = 0
            last_size = 0
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff * (2 ** attempt))

    elapsed_ms = (time.perf_counter() - start) * 1000
    return DownloadResult(url=url, status=last_status, size=last_size, elapsed_ms=round(elapsed_ms, 2))


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
            _download_one(session, url, semaphore, timeout=timeout, max_retries=max_retries)
            for url in urls
        ]
        results: list[DownloadResult] = await asyncio.gather(*tasks)

    return [
        {"url": r.url, "status": r.status,
```
