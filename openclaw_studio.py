#!/usr/bin/env python3
"""
🦞 OpenClaw TUI Studio - 简洁版
单文件运行，无需前后端分离

使用方法:
    python3 openclaw_studio.py

依赖:
    pip install textual aiohttp cryptography
"""

import json
import os
import sys
import time
import uuid
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label, Switch,
    RichLog, ListView, ListItem
)
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual import work

# ============ 数据模型 ============

@dataclass
class EmployeeConfig:
    """员工配置"""
    base_url: str = ""
    token: str = ""
    session_key: str = "default"
    timeout: int = 120
    enabled: bool = True

@dataclass
class Employee:
    """员工"""
    id: str
    name: str
    role: str = "OpenClaw 员工"
    status: str = "offline"
    current_task: str = ""
    unread_count: int = 0
    config: EmployeeConfig = field(default_factory=EmployeeConfig)
    last_error: str = ""

# ============ 数据存储 ============

class DataStore:
    """本地数据存储"""
    
    def __init__(self):
        # 使用项目目录下的 data/ 文件夹
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.identities_dir = self.data_dir / "identities"
        self.identities_dir.mkdir(exist_ok=True)
        self.employees_file = self.data_dir / "employees.json"
        self.employees: Dict[str, Employee] = {}
        self.load()
    
    def load(self):
        """加载数据"""
        if self.employees_file.exists():
            try:
                data = json.loads(self.employees_file.read_text())
                for emp_id, emp_data in data.items():
                    config = EmployeeConfig(**emp_data.pop("config", {}))
                    self.employees[emp_id] = Employee(config=config, **emp_data)
            except Exception as e:
                print(f"加载数据失败: {e}")
        
        # 如果没有员工，创建示例
        if not self.employees:
            self.create_default_employees()
    
    def save(self):
        """保存数据"""
        data = {}
        for emp_id, emp in self.employees.items():
            emp_dict = asdict(emp)
            emp_dict["config"] = asdict(emp.config)
            data[emp_id] = emp_dict
        self.employees_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def create_default_employees(self):
        """创建默认员工"""
        self.employees["emp-001"] = Employee(
            id="emp-001",
            name="Alice",
            role="代码审查专家",
            config=EmployeeConfig(
                base_url="wss://gateway.openclaw.example.com",
                token="your_token_here",
                session_key="alice"
            )
        )
        self.employees["emp-002"] = Employee(
            id="emp-002",
            name="Bob",
            role="文档生成助手",
            config=EmployeeConfig(
                base_url="wss://gateway.openclaw.example.com",
                token="your_token_here",
                session_key="bob"
            )
        )
        self.save()
    
    def add_employee(self, emp: Employee):
        """添加员工"""
        self.employees[emp.id] = emp
        self.save()
    
    def delete_employee(self, emp_id: str):
        """删除员工"""
        if emp_id in self.employees:
            del self.employees[emp_id]
            self.save()
    
    def update_employee(self, emp_id: str, **kwargs):
        """更新员工"""
        if emp_id in self.employees:
            emp = self.employees[emp_id]
            for key, value in kwargs.items():
                if hasattr(emp, key):
                    setattr(emp, key, value)
            self.save()

# ============ OpenClaw 连接 ============

class OpenClawConnection:
    """OpenClaw WebSocket 连接"""
    
    def __init__(self, employee: Employee, on_message=None, on_status=None):
        self.employee = employee
        self.on_message = on_message
        self.on_status = on_status
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self._device_id = ""
        self._device_private_key: Optional[Ed25519PrivateKey] = None
        self._nonce = ""
    
    def _load_or_create_identity(self):
        """加载或创建设备身份"""
        identity_file = Path(__file__).parent / "data" / "identities" / f"{self.employee.id}.json"
        
        if identity_file.exists():
            try:
                data = json.loads(identity_file.read_text())
                pem = data.get("private_key_pem", "")
                if pem:
                    key = serialization.load_pem_private_key(pem.encode(), password=None)
                    if isinstance(key, Ed25519PrivateKey):
                        self._device_private_key = key
                        pub_raw = key.public_key().public_bytes(
                            encoding=serialization.Encoding.Raw,
                            format=serialization.PublicFormat.Raw
                        )
                        self._device_id = hashlib.sha256(pub_raw).hexdigest()
                        return
            except Exception as e:
                print(f"身份加载失败: {e}")
        
        # 创建新身份
        key = Ed25519PrivateKey.generate()
        pub_raw = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self._device_id = hashlib.sha256(pub_raw).hexdigest()
        self._device_private_key = key
        
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        identity_file.write_text(json.dumps({"private_key_pem": pem}, indent=2))
    
    async def connect(self):
        """连接 OpenClaw"""
        if not self.employee.config.enabled or not self.employee.config.base_url:
            return
        
        self._load_or_create_identity()
        
        parsed = urlparse(self.employee.config.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{scheme}://{parsed.netloc}"
        
        headers = {"Origin": f"{parsed.scheme}://{parsed.netloc}"} if parsed.scheme else {}
        
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(ws_url, headers=headers, heartbeat=30)
            
            # 等待 challenge
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("event") == "connect.challenge":
                        self._nonce = data.get("payload", {}).get("nonce", "")
                        await self._send_handshake()
                        self.connected = True
                        self._update_status("idle", "")
                        break
            
            # 启动接收循环
            await self._receive_loop()
            
        except Exception as e:
            self._update_status("offline", str(e))
    
    async def _send_handshake(self):
        """发送握手"""
        if not self._device_private_key:
            return
        
        signed_at = int(time.time() * 1000)
        payload = "|".join([
            "v2", self._device_id, f"studio-{self.employee.id}", "ui", "operator",
            "operator.chat", str(signed_at), self.employee.config.token or "", self._nonce
        ])
        
        signature = self._device_private_key.sign(payload.encode())
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        pub_b64 = base64.urlsafe_b64encode(
            self._device_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode().rstrip("=")
        
        frame = {
            "type": "req",
            "id": str(uuid.uuid4()),
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": f"studio-{self.employee.id}",
                    "version": "0.1.0",
                    "platform": "openclaw-studio",
                    "mode": "ui"
                },
                "role": "operator",
                "scopes": ["operator.chat"],
                "device": {
                    "id": self._device_id,
                    "publicKey": pub_b64,
                    "signature": sig_b64,
                    "signedAt": signed_at,
                    "nonce": self._nonce
                },
                **({"auth": {"token": self.employee.config.token}} if self.employee.config.token else {})
            }
        }
        await self.ws.send_str(json.dumps(frame))
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(json.loads(msg.data))
        except Exception as e:
            print(f"接收错误: {e}")
        finally:
            self.connected = False
            self._update_status("offline", "连接断开")
    
    async def _handle_message(self, data: dict):
        """处理消息"""
        msg_type = data.get("type")
        
        if msg_type == "event" and data.get("event") == "chat":
            payload = data.get("payload", {})
            if payload.get("state") == "final":
                text = self._extract_text(payload.get("message"))
                if self.on_message:
                    self.on_message(text)
    
    def _extract_text(self, message) -> str:
        """提取文本"""
        if isinstance(message, str):
            return message
        if isinstance(message, dict):
            return message.get("content", "") or message.get("text", "")
        return ""
    
    async def send_message(self, content: str) -> str:
        """发送消息"""
        if not self.connected:
            return "❌ 未连接"
        
        try:
            self._update_status("working", "处理中...")
            
            frame = {
                "type": "req",
                "id": str(uuid.uuid4()),
                "method": "chat.send",
                "params": {
                    "sessionKey": f"agent:main:{self.employee.config.session_key}",
                    "message": content,
                    "deliver": False
                }
            }
            await self.ws.send_str(json.dumps(frame))
            
            # 等待回复（简化版）
            return "✅ 消息已发送"
        except Exception as e:
            return f"❌ 发送失败: {e}"
        finally:
            self._update_status("idle", "")
    
    def _update_status(self, status: str, task: str):
        """更新状态"""
        self.employee.status = status
        self.employee.current_task = task
        if self.on_status:
            self.on_status(status, task)
    
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        self.connected = False

# ============ TUI 界面 ============

class EmployeeCard(Vertical):
    """员工卡片"""
    
    DEFAULT_CSS = """
    EmployeeCard {
        width: 28;
        height: 12;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0;
        margin: 0 1 1 0;

    }
    EmployeeCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }
    EmployeeCard:focus { border: solid $accent; }
    EmployeeCard .header {
        height: 3;
        background: $primary-darken-3;
        content-align: center middle;
    }
    EmployeeCard .body {
        height: 6;
        padding: 0 1;
        content-align: center middle;
    }
    EmployeeCard .footer {
        height: 3;
        content-align: center middle;
        color: $text-muted;
    }
    """
    
    def __init__(self, employee: Employee, **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
        self.can_focus = True
    
    def compose(self):
        status_emoji = {"idle": "🟢", "working": "🟡", "offline": "⚫", "error": "🔴"}
        status_text = {"idle": "空闲", "working": "工作中", "offline": "离线", "error": "错误"}
        
        emp = self.employee
        se = status_emoji.get(emp.status, "⚪")
        st = status_text.get(emp.status, "未知")
        
        header = f"{se} {st}"
        if emp.unread_count > 0:
            header += f" 💬{emp.unread_count}"
        
        yield Static(header, classes="header")
        
        with Vertical(classes="body"):
            yield Static("🦞", classes="emoji-icon")
            yield Static(emp.name, classes="name-text")
            yield Static(emp.role, classes="role-text")
        
        task = emp.current_task or "无任务"
        if len(task) > 14:
            task = task[:14] + "..."
        yield Static(f"📋 {task}", classes="footer")
    
    def on_click(self):
        self.app.open_chat(self.employee)
    
    def on_key(self, event):
        if event.key == "enter":
            self.app.open_chat(self.employee)
        elif event.key == "space":
            self.app.show_employee_detail(self.employee)


class MainScreen(Screen):
    """主屏幕"""
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("a", "add_employee", "添加员工"),
        ("r", "refresh", "刷新"),
    ]
    
    employees = reactive(list)
    
    def __init__(self, store: DataStore, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.employees = list(store.employees.values())
        self.connections: Dict[str, OpenClawConnection] = {}
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical():
            with Horizontal(classes="toolbar"):
                yield Button("🔄 刷新", id="refresh", variant="primary")
                yield Button("➕ 添加员工", id="add", variant="success")
            
            yield Static("🦞 OpenClaw Studio - 点击卡片进入对话", classes="title")
            
            # 员工网格
            with Horizontal(id="employee-grid"):
                for emp in self.employees:
                    yield EmployeeCard(emp)
        
        yield Footer()
    
    DEFAULT_CSS = """
    MainScreen .toolbar {
        height: 3;
        background: $surface-darken-1;
        padding: 0 2;
        align: left middle;
    }
    MainScreen .toolbar Button {
        margin-right: 1;
    }
    MainScreen .title {
        height: 2;
        padding: 0 2;
        text-style: bold;
        color: $text-muted;
    }
    MainScreen #employee-grid {
        height: 1fr;
        padding: 1 2;
    }
    """
    
    def on_mount(self):
        """挂载后连接所有启用的员工"""
        for emp in self.employees:
            if emp.config.enabled:
                self.start_connection(emp)
    
    @work
    async def start_connection(self, emp: Employee):
        """启动连接"""
        try:
            conn = OpenClawConnection(
                emp,
                on_message=lambda text, e=emp: self.handle_message(e, text),
                on_status=lambda s, t, e=emp: self.handle_status(e, s, t)
            )
            self.connections[emp.id] = conn
            await conn.connect()
        except Exception as e:
            print(f"[MainScreen] 连接 {emp.name} 失败: {e}")
            emp.status = "offline"
            emp.last_error = str(e)
            self.refresh_employee(emp)
    
    def handle_message(self, emp: Employee, text: str):
        """处理收到的消息"""
        emp.unread_count += 1
        self.refresh_employee(emp)
    
    def handle_status(self, emp: Employee, status: str, task: str):
        """处理状态变化"""
        emp.status = status
        emp.current_task = task
        self.refresh_employee(emp)
    
    def refresh_employee(self, emp: Employee):
        """刷新员工显示"""
        for card in self.query(EmployeeCard):
            if card.employee.id == emp.id:
                card.refresh()
    
    def on_button_pressed(self, event):
        if event.button.id == "refresh":
            self.refresh_employees()
        elif event.button.id == "add":
            self.action_add_employee()
    
    def refresh_employees(self):
        self.employees = list(self.store.employees.values())
        grid = self.query_one("#employee-grid", Horizontal)
        grid.remove_children()
        for emp in self.employees:
            grid.mount(EmployeeCard(emp))
    
    def action_add_employee(self):
        """添加员工"""
        self.notify("添加员工功能开发中...\n请直接编辑 ~/.openclaw_studio/employees.json")
    
    def open_chat(self, employee: Employee):
        """打开聊天"""
        self.push_screen(ChatScreen(employee, self.connections.get(employee.id)))
    
    def show_employee_detail(self, employee: Employee):
        """显示详情"""
        config = employee.config
        text = f"""
员工: {employee.name}
角色: {employee.role}
状态: {employee.status}

OpenClaw 配置:
  Base URL: {config.base_url}
  Token: {config.token[:10]}... if config.token else "未设置"
  Session: {config.session_key}
  Timeout: {config.timeout}s
  Enabled: {config.enabled}
        """
        self.notify(text, title="员工详情", timeout=10)


class ChatScreen(Screen):
    """聊天屏幕"""
    
    BINDINGS = [("escape", "go_back", "返回")]
    
    def __init__(self, employee: Employee, connection: Optional[OpenClawConnection], **kwargs):
        super().__init__(**kwargs)
        self.employee = employee
        self.connection = connection
        self.messages: List[str] = []
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Vertical():
            with Horizontal(classes="chat-header"):
                yield Button("← 返回", id="back", variant="default")
                yield Static(f"🦞 与 {self.employee.name} 对话")
            
            yield RichLog(id="messages", classes="messages")
            
            with Horizontal(classes="input-area"):
                yield Input(placeholder="输入消息...", id="message-input")
                yield Button("发送", id="send", variant="primary")
        
        yield Footer()
    
    DEFAULT_CSS = """
    ChatScreen .chat-header {
        height: 3;
        background: $primary-darken-3;
        padding: 0 1;
        align: left middle;
    }
    ChatScreen .chat-header Static {
        margin-left: 2;
        text-style: bold;
    }
    ChatScreen .messages {
        height: 1fr;
        background: $surface-darken-1;
        padding: 1;
    }
    ChatScreen .input-area {
        height: 3;
        padding: 0 1;
        align: left middle;
    }
    ChatScreen .input-area Input {
        width: 1fr;
    }
    ChatScreen .input-area Button {
        margin-left: 1;
    }
    """
    
    def on_mount(self):
        self.query_one("#message-input", Input).focus()
        self.add_message("系统", f"与 {self.employee.name} 的对话已开始")
        if not self.connection or not self.connection.connected:
            self.add_message("系统", "⚠️ 未连接到 OpenClaw")
    
    def add_message(self, sender: str, content: str):
        """添加消息"""
        log = self.query_one("#messages", RichLog)
        timestamp = datetime.now().strftime("%H:%M")
        log.write(f"[{timestamp}] {sender}: {content}")
    
    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
        elif event.button.id == "send":
            self.send_message()
    
    def on_input_submitted(self, event):
        if event.input.id == "message-input":
            self.send_message()
    
    @work
    async def send_message(self):
        """发送消息"""
        input_widget = self.query_one("#message-input", Input)
        content = input_widget.value.strip()
        if not content:
            return
        
        input_widget.value = ""
        self.add_message("你", content)
        
        if self.connection and self.connection.connected:
            result = await self.connection.send_message(content)
            self.add_message("系统", result)
        else:
            self.add_message("系统", "❌ 未连接，无法发送")
    
    def action_go_back(self):
        self.app.pop_screen()


class OpenClawStudioApp(App):
    """主应用"""
    
    CSS_PATH = None
    mouse_enabled = True
    
    def __init__(self):
        super().__init__()
        self.store = DataStore()
    
    def compose(self) -> ComposeResult:
        yield MainScreen(self.store)
    
    def open_chat(self, employee: Employee):
        """打开聊天（供 EmployeeCard 调用）"""
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.open_chat(employee)
    
    def show_employee_detail(self, employee: Employee):
        """显示详情（供 EmployeeCard 调用）"""
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.show_employee_detail(employee)


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw TUI Studio - 简洁版                        ║
║                                                           ║
║   配置文件: ~/.openclaw_studio/employees.json            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 检查依赖
    try:
        import textual
        import aiohttp
        import cryptography
    except ImportError:
        print("❌ 缺少依赖，请运行:")
        print("   pip install textual aiohttp cryptography")
        sys.exit(1)
    
    app = OpenClawStudioApp()
    app.run()


if __name__ == "__main__":
    main()
