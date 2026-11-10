# 进阶第23节 HTTP 请求的排队与执行耗时

CLI 已用 `append_run_record()` 把任务耗时写入 `runs.jsonl`。HTTP 请求要先拿会话锁，普通请求还要拿全局工作区锁。一次请求可能等锁很久，也可能是模型和工具本身耗时，分别记录才能定位等待发生在哪里。

## 动手 记录两段时间

1. 在 `http_api.py` 导入 `time` 和 `run_records` 中的 `append_run_record`。在 `run_agent_to_queue()` 的 `async with session_lock, workspace_guard:` 前记录 `waiting_started_at = time.perf_counter()`，在进入锁的第一行记录 `started_at = time.perf_counter()`。
2. 在现有的 `finally` 内、通知事件流结束前，调用 `append_run_record()` 写一条字典记录。字段为 `entry`（值是 `"http"`）、`session_id`、`queue_wait_seconds`（`started_at - waiting_started_at`）和 `elapsed_seconds`（`time.perf_counter() - started_at`）。

`queue_wait_seconds` 记录从开始等待到拿到所需锁的时间。`elapsed_seconds` 记录进入锁范围后执行到写日志前的耗时。这一步的记录对应已经取得锁并开始执行的任务。
