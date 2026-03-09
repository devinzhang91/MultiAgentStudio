"""状态栏组件"""
from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    """底部状态栏 - 显示系统状态信息"""
    
    connected = reactive(False)
    online_count = reactive(0)
    total_count = reactive(0)
    task_count = reactive(0)
    
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }
    StatusBar .connected {
        color: $success;
    }
    StatusBar .disconnected {
        color: $error;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_content()
    
    def watch_connected(self, connected: bool):
        """监听连接状态变化"""
        self.update_content()
    
    def watch_online_count(self, count: int):
        """监听在线员工数变化"""
        self.update_content()
    
    def watch_task_count(self, count: int):
        """监听任务数变化"""
        self.update_content()
    
    def update_content(self):
        """更新状态栏内容"""
        status_icon = "🟢" if self.connected else "🔴"
        status_text = "已连接" if self.connected else "未连接"
        
        self.update(
            f"系统状态: {status_icon} {status_text} | "
            f"在线员工: {self.online_count}/{self.total_count} | "
            f"任务队列: {self.task_count}"
        )
