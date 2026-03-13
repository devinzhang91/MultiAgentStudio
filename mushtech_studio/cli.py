"""
CLI子命令入口
提供config、reset、run等子命令
"""

import argparse
import sys
from typing import List, Optional

from .config_screen import run_config_screen
from .reset_manager import run_reset, get_reset_preview
from .config_manager import get_config_manager


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    
    parser = argparse.ArgumentParser(
        prog="mushtech_studio",
        description="🦞 MushTech Studio - 多智能体团队管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 启动主界面（等同于run）
  %(prog)s run                # 启动主界面
  %(prog)s config             # 启动配置界面
  %(prog)s reset              # 重置配置（带确认提示）
  %(prog)s reset --force      # 强制重置（跳过确认）
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # run 命令 - 启动主界面
    run_parser = subparsers.add_parser(
        "run",
        help="启动MushTech Studio主界面",
        description="启动TUI主界面，管理多智能体团队"
    )
    
    # config 命令 - 配置界面
    config_parser = subparsers.add_parser(
        "config",
        help="启动配置界面",
        description="配置Gateway、Workspace、架构和工作室类型"
    )
    
    # reset 命令 - 重置配置
    reset_parser = subparsers.add_parser(
        "reset",
        help="重置所有配置",
        description="重置OpenClaw配置和MushTech Studio配置，并重启Gateway"
    )
    reset_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重置，跳过确认提示"
    )
    
    return parser


def print_reset_preview():
    """打印重置预览信息"""
    try:
        preview = get_reset_preview()
        
        print("\n" + "=" * 60)
        print("⚠️  重置预览信息")
        print("=" * 60)
        print(f"\n工作室类型: {preview['studio_type']}")
        print(f"架构模式:   {preview['architecture']}")
        print(f"Workspace:  {preview['workspace']}")
        print(f"团队规模:   {preview['agents_count']} 位Agent")
        print(f"\n团队成员:")
        for agent in preview['agents']:
            print(f"  {agent['emoji']} {agent['name']} - {agent['role']}")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n[错误] 获取预览信息失败: {e}\n")


def confirm_reset() -> bool:
    """
    确认重置操作
    
    Returns:
        bool: 用户是否确认
    """
    print("\n此操作将执行以下操作:")
    print("  1. 备份当前的 ~/.openclaw/openclaw.json")
    print("  2. 删除旧的 OpenClaw Agent 配置并按当前模板重新创建")
    print("  3. 重置 data/employees.json 与 data/multi_agent_config.json")
    print("  4. 清理本地聊天历史")
    print("  5. 执行 'openclaw gateway restart'")
    print("  6. 通过 Hook 向每位员工会话发送 '/new' 重新建会话")
    print("\n⚠️  警告: 此操作会重置 OpenClaw Studio 当前团队配置，请确保已备份重要数据！")
    
    try:
        response = input("\n确定要继续吗？ [y/N]: ").strip().lower()
        return response in ('y', 'yes')
    except (KeyboardInterrupt, EOFError):
        print("\n")
        return False


def handle_run(args) -> int:
    """
    处理run命令
    
    Returns:
        int: 退出码
    """
    from .app import main as app_main
    return app_main()


def handle_config(args) -> int:
    """
    处理config命令
    
    Returns:
        int: 退出码
    """
    try:
        run_config_screen()
        return 0
    except Exception as e:
        print(f"[错误] 启动配置界面失败: {e}")
        return 1


def handle_reset(args) -> int:
    """
    处理reset命令
    
    Returns:
        int: 退出码
    """
    # 显示预览信息
    print_reset_preview()
    
    # 确认（如非force模式）
    if not args.force:
        if not confirm_reset():
            print("\n已取消重置操作。")
            return 0
    
    print("\n开始重置...")
    print("-" * 60)
    
    # 执行重置
    success, message = run_reset(force=args.force)
    
    print("-" * 60)
    if success:
        print(f"\n✅ {message}")
        print("\n重置完成！如刚刚切换了配置，请等待 Gateway 完全启动后再继续使用。")
        return 0
    else:
        print(f"\n❌ {message}")
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """
    CLI主入口
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # 如果没有指定命令，默认启动run
    command = parsed_args.command or "run"
    
    if command == "run":
        return handle_run(parsed_args)
    elif command == "config":
        return handle_config(parsed_args)
    elif command == "reset":
        return handle_reset(parsed_args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
