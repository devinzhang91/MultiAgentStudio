"""
OpenClaw TUI Studio - 主应用入口

这是一个占位文件，用于展示应用的基本结构。
完整实现请参考 README.md 中的架构设计。
"""

from textual.app import App


class OpenClawStudioApp(App):
    """OpenClaw TUI Studio 主应用类"""
    
    CSS_PATH = "ui/styles/styles.css"
    
    def __init__(self):
        super().__init__()
        # TODO: 初始化配置、状态管理器、OpenClaw 客户端等
    
    def on_mount(self):
        """应用挂载时调用"""
        # TODO: 推送到 Dashboard 屏幕
        pass
    
    async def on_ready(self):
        """应用就绪时调用"""
        # TODO: 启动 webhook 服务器，连接 OpenClaw API
        pass


def main():
    """应用入口函数"""
    app = OpenClawStudioApp()
    app.run()


if __name__ == "__main__":
    main()
