# OpenClaw TUI Studio API 文档

## OpenClaw Webhook 集成

### 发送事件 (Outgoing)

#### POST /webhook/send

发送消息或命令到 OpenClaw 员工。

**请求体:**

```json
{
  "event_type": "task.assign",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {
    "employee_id": "alice-001",
    "session_id": "sess_xxx",
    "message": {
      "content": "请帮我 review 这个 PR",
      "type": "text"
    },
    "context": {
      "project": "my-project",
      "file_path": "/path/to/file.py"
    }
  }
}
```

**响应:**

```json
{
  "status": "accepted",
  "task_id": "task_xxx",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

### 接收事件 (Incoming)

本地 Webhook 服务器接收 OpenClaw 的事件推送。

#### 事件类型

**status.update**

员工状态更新。

```json
{
  "event_type": "status.update",
  "timestamp": "2024-01-15T10:32:00Z",
  "payload": {
    "employee_id": "alice-001",
    "status": "busy",
    "current_task": {
      "task_id": "task_xxx",
      "description": "Reviewing PR #123",
      "progress": 45
    }
  }
}
```

**message.receive**

接收员工回复消息。

```json
{
  "event_type": "message.receive",
  "timestamp": "2024-01-15T10:33:00Z",
  "payload": {
    "employee_id": "alice-001",
    "session_id": "sess_xxx",
    "message": {
      "content": "完成 review，发现 2 个问题...",
      "type": "markdown"
    },
    "reply_to": "msg_xxx"
  }
}
```

**task.complete**

任务完成通知。

```json
{
  "event_type": "task.complete",
  "timestamp": "2024-01-15T10:35:00Z",
  "payload": {
    "employee_id": "alice-001",
    "task_id": "task_xxx",
    "result": {
      "status": "success",
      "output": "...",
      "artifacts": [
        {"type": "file", "path": "/tmp/review.md"}
      ]
    }
  }
}
```

**error.report**

错误报告。

```json
{
  "event_type": "error.report",
  "timestamp": "2024-01-15T10:36:00Z",
  "payload": {
    "employee_id": "alice-001",
    "task_id": "task_xxx",
    "error": {
      "code": "TIMEOUT",
      "message": "Task execution timed out"
    }
  }
}
```

### Webhook 签名验证

所有传入的 Webhook 请求都包含签名头，用于验证来源。

```
X-OpenClaw-Signature: sha256=<hex_signature>
```

验证方法:

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 内部 API

### EmployeeManager

```python
class EmployeeManager:
    async def get_all(self) -> list[Employee]
    async def get(self, employee_id: str) -> Employee | None
    async def update_status(self, employee_id: str, status: Status)
    def subscribe_to_updates(self, callback: Callable)
```

### SessionManager

```python
class SessionManager:
    async def create_session(self, employee_id: str) -> Session
    async def get_session(self, session_id: str) -> Session | None
    async def add_message(self, session_id: str, message: Message)
    async def get_history(self, session_id: str) -> list[Message]
```

### OpenClawClient

```python
class OpenClawClient:
    async def send_message(self, employee_id: str, content: str) -> Task
    async def cancel_task(self, task_id: str) -> bool
    async def query_status(self, employee_id: str) -> Status
```
