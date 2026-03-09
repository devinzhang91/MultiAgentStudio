"""
OpenClaw TUI Studio - 主应用入口

🦞 可视化的二进制 OpenClaw 工作室
在终端中管理你的 OpenClaw AI 员工团队

操作指南:
- ↑/↓/←/→ : 导航员工卡片
- Tab     : 切换焦点
- Enter   : 进入对话/发送消息
- Space   : 查看员工详情
- Esc     : 返回工作室
- q       : 退出应用
"""
import asyncio
from typing import Optional, Any

from textual.app import App, ComposeResult
from textual.reactive import reactive

from .ui.screens.dashboard import DashboardScreen
from .ui.screens.chat import ChatScreen
from .core.state_manager import StateManager
from .core.employee_manager import EmployeeManager
from .openclaw.client import OpenClawClient
from .openclaw.models import Employee, Task, Message


class OpenClawStudioApp(App):
    """OpenClaw TUI Studio 主应用类"""
    
    CSS_PATH = "ui/styles/styles.css"
    
    # 响应式状态
    connected = reactive(False)
    
    BINDINGS = [
        ("q", "quit", "退出(q)"),
        ("r", "action_refresh", "刷新(r)"),
        ("?", "show_help", "帮助(?)"),
    ]
    
    SCREENS = {
        "dashboard": DashboardScreen,
        "chat": ChatScreen,
    }
    
    def __init__(self):
        super().__init__()
        # 初始化核心组件
        self.state_manager = StateManager()
        self.openclaw_client: Optional[OpenClawClient] = None
        self.employee_manager: Optional[EmployeeManager] = None
        
        # 配置（可从配置文件加载）
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置"""
        return {
            "api_base": "https://api.openclaw.ai",
            "api_key": "",
            "webhook_send_url": "",
            "webhook_secret": "",
            "webhook_receive_port": 8765,
            "webhook_receive_path": "/webhook",
        }
    
    def compose(self) -> ComposeResult:
        """组装应用界面"""
        yield DashboardScreen()
    
    async def on_mount(self):
        """应用挂载时调用"""
        if self.config.get("api_key"):
            await self._init_openclaw_client()
        else:
            self.notify("🦞 演示模式 - 使用方向键导航，Enter 对话，q 退出", 
                       severity="information", timeout=5)
            self.state_manager.connected = False
    
    async def _init_openclaw_client(self):
        """初始化 OpenClaw 客户端"""
        try:
            self.openclaw_client = OpenClawClient(
                api_base=self.config["api_base"],
                api_key=self.config["api_key"],
                webhook_send_url=self.config["webhook_send_url"],
                webhook_secret=self.config["webhook_secret"],
                webhook_receive_port=self.config["webhook_receive_port"],
                webhook_receive_path=self.config["webhook_receive_path"],
            )
            
            self.employee_manager = EmployeeManager(
                self.openclaw_client,
                self.state_manager
            )
            
            self.openclaw_client.on_status_update(self._on_status_update)
            self.openclaw_client.on_message_received(self._on_message_received)
            self.openclaw_client.on_task_event(self._on_task_event)
            
            await self.employee_manager.load_employees()
            
            self.connected = True
            self.state_manager.connected = True
            self.notify("🦞 已连接到 OpenClaw！按 ? 查看帮助", severity="information")
            
        except Exception as e:
            self.notify(f"❌ 连接失败: {e}", severity="error")
            self.connected = False
    
    def _on_status_update(self, data: dict):
        """处理状态更新"""
        employee_id = data.get("employee_id")
        status = data.get("status")
        task = data.get("current_task")
        
        if self.employee_manager and employee_id:
            self.employee_manager.update_employee_status(employee_id, status, task)
    
    def _on_message_received(self, data: dict):
        """处理接收到的消息"""
        message = Message(
            id=data.get("message_id", ""),
            employee_id=data.get("employee_id", ""),
            content=data.get("content", ""),
            is_user=False,
        )
        self.state_manager.add_message(message)
    
    def _on_task_event(self, event_type: str, data: dict):
        """处理任务事件"""
        task_id = data.get("task_id")
        if not task_id:
            return
        
        task = self.state_manager.get_task(task_id)
        if task:
            if event_type == "task.complete":
                task.status = "completed"
                task.result = data.get("result")
            elif event_type == "error.report":
                task.status = "failed"
                task.error = data.get("error")
    
    def action_refresh(self):
        """刷新数据"""
        if self.employee_manager:
            asyncio.create_task(self.employee_manager.load_employees())
            self.notify("🔄 刷新中...", severity="information")
        else:
            self.notify("🔄 演示模式 - 模拟刷新", severity="information")
    
    def action_show_help(self):
        """显示帮助"""
        try:
            screen = self.screen
            if hasattr(screen, 'action_show_help'):
                screen.action_show_help()
        except Exception:
            pass
    
    def push_screen(self, screen_name: str, data: dict = None):
        """切换屏幕"""
        if screen_name == "chat" and data:
            employee_id = data.get("employee_id")
            self.push_screen(ChatScreen(employee_id))
        elif screen_name in self.SCREENS:
            self.push_screen(self.SCREENS[screen_name]())
        else:
            super().push_screen(screen_name)
    
    async def send_to_employee(self, employee_id: str, content: str):
        """发送消息给员工"""
        if not self.openclaw_client:
            # 演示模式 - 模拟响应
            await self._simulate_response(employee_id, content)
            return
        
        message = await self.openclaw_client.send_message(employee_id, content)
        if message:
            self.state_manager.add_message(message)
            self.notify(f"📤 已发送", severity="information")
        else:
            self.notify("❌ 发送失败", severity="error")
    
    async def _simulate_response(self, employee_id: str, content: str):
        """演示模式 - 模拟员工响应"""
        await asyncio.sleep(1.5)
        
        # 获取员工名称
        employee_name = "Unknown"
        for emp in self.state_manager.get_employees_list():
            if emp.id == employee_id:
                employee_name = emp.name
                break
        
        # 模拟响应
        responses = {
            "alice-001": f"✅ 收到！我是 {employee_name}，正在分析代码...",
            "bob-002": f"📝 {employee_name} 开始生成文档，请稍等。",
            "carol-003": f"🧪 {employee_name} 准备执行测试。",
            "dave-004": "⚫ 抱歉，我当前离线。",
            "eve-005": f"📊 {employee_name} 正在处理数据分析...",
        }
        
        response = responses.get(
            employee_id,
            f"🦞 {employee_name} 收到: {content[:20]}..."
        )
        
        # 更新聊天界面
        try:
            chat_screen = self.screen
            if isinstance(chat_screen, ChatScreen):
                chat_screen.on_chat_message(response)
        except Exception:
            pass
    
    def on_key(self, event):
        """全局键盘处理"""
        # 问号键显示帮助
        if event.character == "?":
            self.action_show_help()
            event.stop()


def main():
    """应用入口函数"""
    app = OpenClawStudioApp()
    app.run()


if __name__ == "__main__":
    main()
