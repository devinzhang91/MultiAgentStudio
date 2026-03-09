"""
OpenClaw TUI Studio - 主应用入口

可视化的二进制 OpenClaw 工作室 - 在终端中管理你的 OpenClaw AI 员工团队
"""
import asyncio
from typing import Optional, Any

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
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
        ("q", "quit", "退出"),
        ("r", "refresh", "刷新"),
        ("d", "push_screen('dashboard')", "主面板"),
        ("?", "push_screen('help')", "帮助"),
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
        # 默认配置
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
        yield Header(show_clock=True)
        yield DashboardScreen()
        yield Footer()
    
    async def on_mount(self):
        """应用挂载时调用"""
        # 初始化 OpenClaw 客户端
        if self.config.get("api_key"):
            await self._init_openclaw_client()
        else:
            # 演示模式 - 无真实连接
            self.notify("运行模式: 演示模式 (未配置 OpenClaw API)", severity="warning")
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
            
            # 初始化员工管理器
            self.employee_manager = EmployeeManager(
                self.openclaw_client,
                self.state_manager
            )
            
            # 注册 webhook 回调
            self.openclaw_client.on_status_update(self._on_status_update)
            self.openclaw_client.on_message_received(self._on_message_received)
            self.openclaw_client.on_task_event(self._on_task_event)
            
            # 加载员工列表
            await self.employee_manager.load_employees()
            
            # 标记为已连接
            self.connected = True
            self.state_manager.connected = True
            self.notify("已连接到 OpenClaw", severity="information")
            
        except Exception as e:
            self.notify(f"连接 OpenClaw 失败: {e}", severity="error")
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
        
        # 如果在聊天界面，更新显示
        # TODO: 通知当前聊天界面
    
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
            self.notify("正在刷新数据...", severity="information")
        else:
            self.notify("未连接到 OpenClaw", severity="warning")
    
    def push_screen(self, screen_name: str, data: dict = None):
        """切换屏幕"""
        if screen_name == "chat" and data:
            employee_id = data.get("employee_id")
            self.push_screen(ChatScreen(employee_id))
        elif screen_name in self.SCREENS:
            self.push_screen(self.SCREENS[screen_name]())
        else:
            super().push_screen(screen_name)
    
    def show_employee_detail(self, employee_id: str):
        """显示员工详情"""
        employee = self.state_manager.get_employee(employee_id)
        if employee:
            self.notify(f"员工详情: {employee.name}\n角色: {employee.role}\n状态: {employee.status.value}")
    
    async def send_to_employee(self, employee_id: str, content: str):
        """发送消息给员工"""
        if not self.openclaw_client:
            # 演示模式 - 模拟响应
            await self._simulate_response(employee_id, content)
            return
        
        # 发送消息
        message = await self.openclaw_client.send_message(employee_id, content)
        if message:
            self.state_manager.add_message(message)
            self.notify(f"消息已发送给 {employee_id}", severity="information")
        else:
            self.notify("发送失败", severity="error")
    
    async def _simulate_response(self, employee_id: str, content: str):
        """演示模式 - 模拟员工响应"""
        await asyncio.sleep(1)
        
        # 获取员工信息
        employee_name = "Unknown"
        for emp in self.state_manager.get_employees_list():
            if emp.id == employee_id:
                employee_name = emp.name
                break
        
        # 简单响应逻辑
        responses = {
            "alice-001": f"收到！我是 {employee_name}，开始处理您的代码审查请求。",
            "bob-002": f"好的，{employee_name} 正在为您生成文档...",
            "carol-003": f"{employee_name} 收到，准备执行测试任务。",
            "dave-004": "抱歉，我当前处于离线状态。",
            "eve-005": f"{employee_name} 开始分析数据...",
        }
        
        response = responses.get(
            employee_id,
            f"{employee_name} 收到您的消息: {content[:20]}..."
        )
        
        # 添加消息到状态
        message = Message(
            id=f"msg-{asyncio.get_event_loop().time()}",
            employee_id=employee_id,
            content=response,
            is_user=False,
        )
        self.state_manager.add_message(message)
        
        # 尝试更新当前聊天界面
        try:
            chat_screen = self.screen
            if hasattr(chat_screen, 'on_chat_message'):
                chat_screen.on_chat_message(response)
        except Exception:
            pass
    
    async def on_ready(self):
        """应用就绪时调用"""
        pass


def main():
    """应用入口函数"""
    app = OpenClawStudioApp()
    app.run()


if __name__ == "__main__":
    main()
