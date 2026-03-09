"""
OpenClaw TUI Frontend
员工管理 + 聊天界面
"""
import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.reactive import reactive

from .api_client import BackendClient
from .screens.dashboard import DashboardScreen
from .screens.employee_property import EmployeePropertyScreen
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
    
    def compose(self) -> ComposeResult:
        yield DashboardScreen()
    
    def on_mount(self):
        """挂载后连接 WebSocket"""
        # 启动 WebSocket 连接
        asyncio.create_task(self.client.connect_websocket())
        self.notify("🦞 连接到后端服务...")
    
    def open_chat(self, employee_id: str):
        """打开聊天界面"""
        self.push_screen(ChatScreen(employee_id))
    
    def show_employee_detail(self, employee_id: str):
        """显示员工属性"""
        # 使用 asyncio.create_task 异步获取数据
        async def load_and_show():
            emp = await self.client.get_employee(employee_id)
            if emp:
                self.push_screen(EmployeePropertyScreen(emp))
        
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
