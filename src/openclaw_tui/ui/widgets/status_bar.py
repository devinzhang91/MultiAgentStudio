"""状态栏组件 - 平面风格"""
from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    """底部状态栏 - 简洁平面风格"""
    
    connected = reactive(False)
    online_count = reactive(0)
    total_count = reactive(0)
    task_count = reactive(0)
    unread_total = reactive(0)
    
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-3;
        color: $text;
        content-align: center middle;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_content()
    
    def watch_connected(self, connected: bool):
        self.update_content()
    
    def watch_online_count(self, count: int):
        self.update_content()
    
    def watch_task_count(self, count: int):
        self.update_content()
    
    def watch_unread_total(self, count: int):
        self.update_content()
    
    def update_content(self):
        """更新状态栏内容 - 使用emoji"""
        conn_emoji = "🟢" if self.connected else "🔴"
        conn_text = "已连接" if self.connected else "未连接"
        
        parts = [
            f"{conn_emoji} {conn_text}",
            f"🦞 {self.online_count}/{self.total_count}",
            f"📋 {self.task_count}",
        ]
        
        if self.unread_total > 0:
            parts.append(f"💬 {self.unread_total}")
        
        self.update("  │  ".join(parts))
