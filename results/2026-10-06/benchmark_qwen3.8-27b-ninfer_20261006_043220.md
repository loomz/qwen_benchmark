# Qwen 编码能力 & 效率基准测试 (qwen3.8-27b, profile=qwen3.8-27b-ninfer)

时间: 2026-10-06 04:33:32
硬件: RTX 5090D 24G
服务端: llama-swap @ http://localhost:8080/v1/chat/completions -> llama-server :5804
每任务运行: 3 次
reasoning_effort: medium  |  max_tokens: 16384

## 0. 当前 llama-server 配置 (qwen3.8-27b, profile=qwen3.8-27b-ninfer, 原样记录)

> ⚠️ 配置读取: cmdline OK, /props failed: 404 Client Error: Not Found for url: http://127.0.0.1:5804/props

**进程** (PID 46512, port 5804):

```bash
/home/loomz/.llama.cpp/ninfer/ninfer/build/apps/ninfer-serve
  /home/loomz/.llama.cpp/ninfer/models/qwen3.8-27b-lynn-nf4.ninfer
  --prefill-chunk 4096
  --max-context 207000
  --kv-capacity 207000
  --max-concurrency 1
  --device-state-slots 1
  --kv-dtype nvfp4
  --spec dflash2
  --draft-tokens 8
  --lm-head-draft
  --chat-template /home/loomz/.llama.cpp/llama-swap/qwen3.8-tolerant-sys.jinja
  --port 5804
  --model-id qwen3.8-27b
```

> \* 速度为客户端估算: 生成速度=输出Tok/首Tok后耗时, Prompt速度=输入Tok/首Tok延迟; 总Tok 来自 API usage (精确)。
> 推理词数/代码词数为按空格分词的估算值 (非精确token数); 通过率仅统计 verify=True 的任务。

## qwen3.8-27b

| 任务 | # | TTFT推理(s) | TTFT代码(s) | 总耗时(s) | 推理词数(估) | 代码词数(估) | 总Tok | 生成Tok/s* | 通过 |
|------|---|-------------|-------------|----------|---------|---------|-------|-------------|------|
| Fibonacci Memoization | 1 | 0.06 | 2.33 | 2.64 | 182 | 61 | 807 | 312.8 | Y |
| Fibonacci Memoization | 2 | 0.04 | 0.72 | 1.11 | 63 | 73 | 377 | 351.1 | Y |
| Fibonacci Memoization | 3 | 0.04 | 1.23 | 1.53 | 90 | 55 | 540 | 361.7 | Y |
| LRU Cache | 1 | 0.06 | 1.55 | 3.60 | 167 | 276 | 1293 | 365.8 | Y |
| LRU Cache | 2 | 0.04 | 1.27 | 3.35 | 151 | 280 | 1243 | 375.4 | Y |
| LRU Cache | 3 | 0.04 | 1.69 | 4.10 | 165 | 316 | 1367 | 336.4 | Y |
| Async Task Queue | 1 | 0.06 | 7.45 | 10.60 | 989 | 349 | 3257 | 309.0 | - |
| Async Task Queue | 2 | 0.04 | 5.34 | 8.82 | 663 | 436 | 2902 | 330.6 | - |
| Async Task Queue | 3 | 0.04 | 4.83 | 7.69 | 354 | 352 | 2228 | 291.3 | - |
| SQL Parser | 1 | 0.06 | 4.20 | 6.04 | 321 | 250 | 1958 | 327.1 | Y |
| SQL Parser | 2 | 0.04 | 3.07 | 4.63 | 246 | 234 | 1522 | 331.9 | Y |
| SQL Parser | 3 | 0.04 | 3.35 | 5.20 | 303 | 267 | 1895 | 367.3 | Y |
| HTTP Downloader | 1 | 0.06 | 0.61 | 2.25 | 80 | 200 | 708 | 323.7 | - |
| HTTP Downloader | 2 | 0.04 | 0.60 | 2.58 | 91 | 238 | 868 | 341.2 | - |
| HTTP Downloader | 3 | 0.04 | 0.52 | 2.56 | 78 | 223 | 863 | 341.9 | - |

**均值**: TTFT推理=0.05s, TTFT代码=2.58s, 总耗时=4.45s, 推理词数(估)=263, 代码词数(估)=241, 服务端Tok/s=337.8, PromptTok/s=2186.5, 通过率=9/9 (仅verify任务)

## 对比总结

| 指标 | qwen3.8-27b |
|------|-------|
| 首字延迟-推理 (s) | 0.05 |
| 首字延迟-代码 (s) | 2.58 |
| 总耗时 (s) | 4.45 |
| 生成速度 (tok/s)* | 337.8 |
| Prompt 速度 (tok/s)* | 2186.5 |
| 推理词数(估) | 263 |
| 代码词数(估) | 241 |
| 代码通过率(仅verify) | 100% (9/9) |

## 代码输出样例

### qwen3.8-27b - Fibonacci Memoization
**执行: PASS**

```python
```python
from functools import wraps

def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper

@memoize
def fibonacci(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)

assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(20) == 6765
```
```

### qwen3.8-27b - LRU Cache
**执行: PASS**

```python
```python
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Hashable


class LRUCache:
    """Thread-safe LRU Cache with O(1) get/put."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity: int = capacity
        self._store: OrderedDict[Hashable, Any] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            return self._store[key]

    def put(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = value
            else:
                if len(self._store) >= self._capacity:
                    self._store.popitem(last=False)
                self._store[key] = value

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# ─────────────────────────── Tests ───────────────────────────

def test_basic_lru_eviction() -> None:
    cache: LRUCache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1          # 'a' becomes most-recent
    cache.put("c", 3)                  # evicts 'b'
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    print("✓ test_basic_lru_eviction passed")


def test_update_existing_key() -> None:
    cache: LRUCache = LRUCache(2)
    cache.put("x", 10)
    cache.put("y", 20)
    cache.put("x", 99)                 # update, not insert
    assert cache.size == 2
    assert cache.get("x") == 99
    cache.put("z", 30)                # evicts 'y'
    assert cache.get("y") is None
    assert cache.get("x") == 99
    assert
```

### qwen3.8-27b - Async Task Queue

```python
```python
import asyncio
import heapq
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass(order=True)
class Task:
    priority: int
    seq: int
    task_id: str = field(compare=False, default="")
    factory: Any = field(compare=False, default=None)


class TaskQueue:
    """异步任务队列：优先级调度 + 指数退避重试 + 可配置并发"""

    def __init__(self, concurrency: int = 3, max_retries: int = 3, backoff_base: float = 0.5):
        self._heap: list[Task] = []
        self._seq = 0
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.stats = {"completed": 0, "failed": 0, "retried": 0}
        self._lock = asyncio.Lock()

    def submit(self, factory: Callable[[], Coroutine], priority: int = 5, task_id: str = "") -> str:
        """提交任务。factory 是返回协程的可调用对象（每次重试重新调用）。"""
        if not task_id:
            task_id = f"task_{self._seq}"
        task = Task(priority=priority, seq=self._seq, task_id=task_id, factory=factory)
        heapq.heappush(self._heap, task)
        self._seq += 1
        return task_id

    async def _execute(self, task: Task) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                result = await task.factory()
                async with self._lock:
                    self.stats["completed"] += 1
                print(f"  [OK]    {task.task_id}  pri={task.priority}  attempt={attempt + 1}")
                return result
            except Exception as e:
                if attempt < self.max_retries:
                    async with self._lock:
                        self.stats["retried"] += 1
                    delay = self.backoff_base * (2 ** attempt)
                    print(f"  [RETRY] {task.task_id}  attempt={attempt + 1}  err={e!r}  backoff={delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    async with self._lock:
                       
```

### qwen3.8-27b - SQL Parser
**执行: PASS**

```python
```python
import re
import unittest


def parse_sql(sql: str) -> dict:
    """解析简单 SQL: SELECT col FROM table WHERE cond"""
    sql = sql.strip().rstrip(';').strip()

    pattern = re.compile(
        r'^\s*SELECT\s+(?P<columns>.+?)\s+FROM\s+(?P<table>\w+)(?:\s+WHERE\s+(?P<where>.+))?\s*$',
        re.IGNORECASE,
    )

    m = pattern.match(sql)
    if not m:
        raise ValueError(f"Cannot parse SQL: {sql!r}")

    # 解析列
    columns_raw = m.group('columns').strip()
    if columns_raw == '*':
        selected_columns = ['*']
    else:
        selected_columns = [c.strip() for c in columns_raw.split(',')]

    table_name = m.group('table').strip()

    # 解析 WHERE（按 AND 分割为多个条件）
    where_raw = m.group('where')
    if where_raw:
        where_conditions = [c.strip() for c in re.split(r'\s+AND\s+', where_raw, flags=re.IGNORECASE)]
    else:
        where_conditions = []

    return {
        'selected_columns': selected_columns,
        'table_name': table_name,
        'where_conditions': where_conditions,
    }


class TestSqlParser(unittest.TestCase):

    def test_simple_select_no_where(self):
        result = parse_sql("SELECT name FROM users")
        self.assertEqual(result['selected_columns'], ['name'])
        self.assertEqual(result['table_name'], 'users')
        self.assertEqual(result['where_conditions'], [])

    def test_select_multiple_columns_with_where(self):
        result = parse_sql("SELECT name, age FROM users WHERE age > 18")
        self.assertEqual(result['selected_columns'], ['name', 'age'])
        self.assertEqual(result['table_name'], 'users')
        self.assertEqual(result['where_conditions'], ['age > 18'])

    def test_select_star(self):
        result = parse_sql("SELECT * FROM orders WHERE status = 'active'")
        self.assertEqual(result['selected_columns'], ['*'])
        self.assertEqual(result['table_name'], 'orders')
        self.assertEqual(result['where_conditions'], ["status = 'active'"])

    def test_multiple_and_condit
```

### qwen3.8-27b - HTTP Downloader

```python
```python
import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

import aiohttp


@dataclass
class DownloadResult:
    url: str
    status: int
    size: int
    elapsed_ms: float


async def download_urls(
    urls: List[str],
    *,
    max_concurrency: int = 10,
    timeout_sec: float = 30.0,
    retries: int = 3,
    backoff: float = 1.0,
) -> List[Dict[str, Any]]:
    semaphore = asyncio.Semaphore(max_concurrency)
    timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async def _download_one(url: str) -> Dict[str, Any]:
            async with semaphore:
                last_exc: Exception | None = None
                for attempt in range(1, retries + 1):
                    start = time.perf_counter()
                    try:
                        async with session.get(url) as resp:
                            body = await resp.read()
                            elapsed_ms = (time.perf_counter() - start) * 1000
                            return {
                                "url": url,
                                "status": resp.status,
                                "size": len(body),
                                "elapsed_ms": round(elapsed_ms, 2),
                            }
                    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                        last_exc = exc
                        if attempt < retries:
                            await asyncio.sleep(backoff * (2 ** (attempt - 1)))
                # all retries exhausted
                return {
                    "url": url,
                    "status": -1,
                    "size": 0,
                    "elapsed_ms": 0.0,
                    "error": str(last_exc),
                }

        tasks = [asyncio.create_task(_download_one(u)) for u in urls]
        results = await asyncio.gather(*tasks)
        return list(results)



```
