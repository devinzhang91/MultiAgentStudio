"""
OpenClaw TUI Frontend
员工管理 + 聊天界面
"""
import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.reactive import reactive

from .api_client import BackendClient
from .screens.dashboard import DashboardScreen, EmployeePropertyScreen
from .screens.chat import ChatScreen


class OpenClawFrontendApp(App):
    """TUI 前端主应用"""
    
    CSS_PATH = None
    mouse_enabled = True
    
    BINDINGS = [
        ("q", "quit", "退出"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = BackendClient()
        self._connected = False
    
    def compose(self) -> ComposeResult:
        yield DashboardScreen()
    
    async def on_mount(self):
        """挂载后连接后端"""
        # 注册 WebSocket 事件
        self.client.on("employee_created", self.on_employee_changed)
        self.client.on("employee_updated", self.on_employee_changed)
        self.client.on("employee_deleted", self.on_employee_deleted)
        self.client.on("employee_status_changed", self.on_status_changed)
        self.client.on("new_message", self.on_new_message)
        
        # 连接 WebSocket
        await self.client.connect_websocket()
        
        self.notify("🦞 已连接到后端服务")
    
    def on_employee_changed(self, data):
        """员工数据变化"""
        # 刷新当前屏幕
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.load_employees()
    
    def on_employee_deleted(self, data):
        """员工被删除"""
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.load_employees()
    
    def on_status_changed(self, data):
        """员工状态变化"""
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            # 更新特定员工状态
            for card in screen.query(EmployeeCard):
                if card.employee_id == data.get("employee_id"):
                    card.status = data.get("status", card.status)
                    card.current_task = data.get("current_task", card.current_task)
    
    def on_new_message(self, data):
        """新消息"""
        screen = self.screen
        if isinstance(screen, ChatScreen):
            if screen.employee_id == data.get("employee_id"):
                screen.load_messages()
    
    def open_chat(self, employee_id: str):
        """打开聊天界面"""
        self.push_screen(ChatScreen(employee_id))
    
    def show_employee_detail(self, employee_id: str):
        """显示员工属性"""
        # 查找员工数据
        async def load_and_show():
            emp = await self.client.get_employee(employee_id)
            if emp:
                self.call_from_thread(lambda: self.push_screen(EmployeePropertyScreen(emp)))
        
        asyncio.create_task(load_and_show())


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🦞 OpenClaw Frontend (TUI) v0.2.0                       ║
║                                                           ║
║   连接到后端: http://localhost:18765                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    app = OpenClawFrontendApp()
    app.run()


if __name__ == "__main__":
    main()
