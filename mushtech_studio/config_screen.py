"""
MushTech Studio 配置界面

纯键盘流程：
- ↑/↓ 选择配置项
- Enter 打开编辑/选择弹窗
- 弹窗中 Enter 确认，ESC 取消
- 配置保存后需单独执行 reset 子命令生效
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Static

from .config_manager import StudioConfig, get_architecture_options, get_config_manager
from .templates import get_template, list_templates


@dataclass(frozen=True)
class ConfigItem:
    key: str
    label: str
    kind: str
    section: str
    description: str
    is_password: bool = False


class TextInputDialog(ModalScreen):
    """文本编辑弹窗"""

    CSS = """
    TextInputDialog {
        align: center middle;
    }

    .dialog {
        width: 84;
        max-width: 96%;
        height: auto;
        background: black;
        border: solid green;
        padding: 1 2;
    }

    .dialog-title {
        color: green;
        text-style: bold;
        margin-bottom: 1;
    }

    .dialog-desc {
        color: ansi_bright_green;
        margin-bottom: 1;
    }

    .dialog-input {
        width: 100%;
        background: black;
        color: green;
        border: solid darkgreen;
    }

    .dialog-hint {
        color: darkgreen;
        margin-top: 1;
    }
    """

    def __init__(self, title: str, description: str, value: str, is_password: bool = False):
        super().__init__()
        self.title = title
        self.description = description
        self.value = value
        self.is_password = is_password

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(self.title, classes="dialog-title")
            yield Static(self.description, classes="dialog-desc")
            yield Input(
                value=self.value,
                password=self.is_password,
                id="dialog-input",
                classes="dialog-input",
            )
            yield Static("Enter 确认修改 | ESC 关闭弹窗", classes="dialog-hint")

    def on_mount(self) -> None:
        self.query_one("#dialog-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class ChoiceDialog(ModalScreen):
    """单选弹窗"""

    CSS = """
    ChoiceDialog {
        align: center middle;
    }

    .dialog {
        width: 92;
        max-width: 96%;
        height: auto;
        background: black;
        border: solid green;
        padding: 1 2;
    }

    .dialog-title {
        color: green;
        text-style: bold;
        margin-bottom: 1;
    }

    .dialog-desc {
        color: ansi_bright_green;
        margin-bottom: 1;
    }

    .choice-item {
        margin: 1 0;
        padding: 0 1;
        color: green;
        border: tall black;
    }

    .choice-item-selected {
        background: darkgreen;
        color: black;
        text-style: bold;
    }

    .dialog-hint {
        color: darkgreen;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("up", "move_up", "上移"),
        ("down", "move_down", "下移"),
        ("enter", "confirm", "确认"),
        ("escape", "cancel", "取消"),
    ]

    focused_index = reactive(0)

    def __init__(self, title: str, description: str, options: list[dict[str, str]], current_value: str):
        super().__init__()
        self.title = title
        self.description = description
        self.options = options
        self.current_value = current_value

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(self.title, classes="dialog-title")
            yield Static(self.description, classes="dialog-desc")
            for index, _option in enumerate(self.options):
                yield Static(self._render_option(index), id=f"choice_{index}", classes="choice-item")
            yield Static("↑/↓ 选择 | Enter 确认修改 | ESC 关闭弹窗", classes="dialog-hint")

    def on_mount(self) -> None:
        for index, option in enumerate(self.options):
            if option["value"] == self.current_value:
                self.focused_index = index
                break
        self._refresh_options()

    def watch_focused_index(self, old_value: int, new_value: int) -> None:
        if old_value != new_value:
            self._refresh_options()

    def _render_option(self, index: int) -> str:
        option = self.options[index]
        active_marker = "▶" if index == self.focused_index else " "
        selected_marker = "●" if option["value"] == self.current_value else "○"
        return f"{active_marker} {selected_marker} {option['label']}\n    {option.get('description', '')}"

    def _refresh_options(self) -> None:
        for index, _option in enumerate(self.options):
            widget = self.query_one(f"#choice_{index}", Static)
            widget.update(self._render_option(index))
            widget.remove_class("choice-item-selected")
            if index == self.focused_index:
                widget.add_class("choice-item-selected")
                widget.scroll_visible()

    def action_move_up(self) -> None:
        if self.focused_index > 0:
            self.focused_index -= 1

    def action_move_down(self) -> None:
        if self.focused_index < len(self.options) - 1:
            self.focused_index += 1

    def action_confirm(self) -> None:
        self.dismiss(self.options[self.focused_index]["value"])

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmSaveDialog(ModalScreen):
    """保存确认弹窗"""

    CSS = """
    ConfirmSaveDialog {
        align: center middle;
    }

    .dialog {
        width: 92;
        max-width: 96%;
        height: auto;
        background: black;
        border: solid yellow;
        padding: 1 2;
    }

    .dialog-title {
        color: yellow;
        text-style: bold;
        margin-bottom: 1;
    }

    .dialog-content {
        color: green;
    }

    .dialog-hint {
        color: darkgreen;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("enter", "confirm", "确认"),
        ("escape", "cancel", "取消"),
    ]

    def __init__(self, summary: str):
        super().__init__()
        self.summary = summary

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static("确认保存配置", classes="dialog-title")
            yield Static(self.summary, classes="dialog-content")
            yield Static("Enter 保存配置 | ESC 返回配置界面", classes="dialog-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ConfigScreen(Screen):
    """配置主界面"""

    CSS = """
    .screen {
        width: 100%;
        height: 100%;
        background: black;
        color: green;
    }

    .header {
        height: 3;
        padding: 0 2;
        border-bottom: solid green;
    }

    .title {
        color: green;
        text-style: bold;
    }

    .subtitle {
        color: darkgreen;
    }

    .body {
        height: 1fr;
    }

    .panel {
        height: 100%;
        margin: 1;
        border: solid darkgreen;
        padding: 1;
    }

    .main-panel {
        width: 2fr;
    }

    .side-panel {
        width: 1fr;
    }

    .panel-title {
        color: green;
        text-style: bold;
        margin-bottom: 1;
    }

    .panel-scroll {
        height: 1fr;
    }

    .section-title {
        color: ansi_bright_green;
        text-style: bold;
        margin: 1 0 0 0;
    }

    .config-row {
        margin: 0 0 1 0;
        padding: 0 1;
        color: green;
    }

    .config-row-focused {
        background: darkgreen;
        color: black;
        text-style: bold;
    }

    .detail {
        color: ansi_bright_green;
    }

    .message {
        height: 2;
        margin: 0 1 1 1;
        padding: 0 1;
        border-top: solid darkgreen;
        color: green;
    }

    .hint {
        height: 1;
        padding: 0 2;
        color: darkgreen;
        border-top: solid darkgreen;
    }
    """

    BINDINGS = [
        ("up", "move_up", "上移"),
        ("down", "move_down", "下移"),
        ("enter", "select", "选择"),
        ("escape", "quit", "退出"),
    ]

    focused_index = reactive(0)

    def __init__(self):
        super().__init__()
        self.config_mgr = get_config_manager()
        self.original_config = StudioConfig.from_dict(self.config_mgr.get_config().to_dict())
        self.config = StudioConfig.from_dict(self.original_config.to_dict())
        self.architecture_options = get_architecture_options()
        self.template_options = [
            {
                "value": template["id"],
                "label": template["name"],
                "description": template["description"],
            }
            for template in list_templates()
        ]
        self.items = self._build_items()

    def _build_items(self) -> list[ConfigItem]:
        return [
            ConfigItem(
                key="token",
                label="Gateway Token",
                kind="text",
                section="Gateway",
                description="用于连接 OpenClaw Gateway 的鉴权 Token。默认读取本地 ~/.openclaw/openclaw.json 的 gateway.auth.token（若无则回退 hooks.token）。保存时仅写入 studio_config.json，不会回写 ~/.openclaw/openclaw.json。",
                is_password=True,
            ),
            ConfigItem(
                key="host",
                label="Gateway IP 地址",
                kind="text",
                section="Gateway",
                description="Gateway 的监听 IP 或访问地址。127.0.0.1 / localhost 会使用 loopback，其他地址会写入自定义绑定主机。",
            ),
            ConfigItem(
                key="port",
                label="Gateway 端口",
                kind="text",
                section="Gateway",
                description="Gateway 监听端口。reset 时会同步写入 ~/.openclaw/openclaw.json 的 gateway.port。",
            ),
            ConfigItem(
                key="workspace",
                label="Workspace 路径",
                kind="text",
                section="Workspace",
                description="工作室根目录。默认路径为 /Users/<username>/MushTech-openclaw，reset 时会自动创建子目录。",
            ),
            ConfigItem(
                key="architecture",
                label="工作室架构",
                kind="choice",
                section="Studio",
                description="选择团队协作架构。Enter 后弹出架构选择窗口，ESC 关闭，Enter 确认。",
            ),
            ConfigItem(
                key="studio_type",
                label="工作室模板",
                kind="choice",
                section="Studio",
                description="选择 MushTech Studio 预置模板。模板决定默认角色分工、成员配置和默认团队结构。",
            ),
            ConfigItem(
                key="save",
                label="保存配置",
                kind="action",
                section="操作",
                description="保存到 data/studio_config.json。注意：保存后不会自动 reset，需单独执行 mushtech_studio reset 才会生效。",
            ),
            ConfigItem(
                key="quit",
                label="退出配置界面",
                kind="action",
                section="操作",
                description="退出当前配置界面。若有未保存修改，将仅退出界面，不会写入配置文件。",
            ),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="screen"):
            with Vertical(classes="header"):
                yield Static("🦞 MushTech Studio · Config", classes="title")
                yield Static(
                    "使用 Enter 打开编辑窗口；弹窗中 Enter 确认修改，ESC 关闭窗口。保存后需单独执行 reset。",
                    classes="subtitle",
                )

            with Horizontal(classes="body"):
                with Vertical(classes="panel main-panel"):
                    yield Static("配置项", classes="panel-title")
                    with ScrollableContainer(id="config-list", classes="panel-scroll"):
                        current_section = None
                        for item in self.items:
                            if item.section != current_section:
                                current_section = item.section
                                yield Static(current_section, classes="section-title")
                            yield Static("", id=f"row_{item.key}", classes="config-row")

                with Vertical(classes="panel side-panel"):
                    yield Static("说明 / 预览", classes="panel-title")
                    with ScrollableContainer(id="detail-scroll", classes="panel-scroll"):
                        yield Static("", id="detail", classes="detail")

            yield Static("", id="message", classes="message")
            yield Static("↑/↓ 移动 | Enter 编辑/选择 | ESC 退出", classes="hint")

    def on_mount(self) -> None:
        self._refresh_all()

    def on_key(self, event) -> None:
        """统一接管主界面按键，避免ScrollableContainer吞掉方向键导致只滚动不选中。"""
        if event.key == "up":
            event.stop()
            self.action_move_up()
            return
        if event.key == "down":
            event.stop()
            self.action_move_down()
            return
        if event.key == "enter":
            event.stop()
            self.action_select()
            return
        if event.key == "escape":
            event.stop()
            self.action_quit()
            return

    def watch_focused_index(self, old_value: int, new_value: int) -> None:
        if old_value != new_value:
            self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_rows()
        self._refresh_detail()

    def _has_unsaved_changes(self) -> bool:
        return self.config.to_dict() != self.original_config.to_dict()

    def _mask(self, value: str) -> str:
        if not value:
            return "(未设置)"
        return "●" * min(len(value), 20)

    def _value_for_item(self, item: ConfigItem) -> str:
        if item.key == "token":
            return self._mask(self.config.gateway_token)
        if item.key == "host":
            return self.config.gateway_host or "(未设置)"
        if item.key == "port":
            return str(self.config.gateway_port)
        if item.key == "workspace":
            return self.config.base_workspace or "(未设置)"
        if item.key == "architecture":
            return self.config.get_architecture_display_name()
        if item.key == "studio_type":
            return self.config.get_studio_type_display_name()
        if item.key == "save":
            return "写入 studio_config.json"
        if item.key == "quit":
            return "关闭配置界面"
        return ""

    def _render_row(self, item: ConfigItem, selected: bool) -> str:
        pointer = "▶" if selected else " "
        dirty = " *" if self._has_item_changed(item.key) else ""
        return f"{pointer} {item.label}: {self._value_for_item(item)}{dirty}"

    def _has_item_changed(self, item_key: str) -> bool:
        field_map = {
            "token": "gateway_token",
            "host": "gateway_host",
            "port": "gateway_port",
            "workspace": "base_workspace",
            "architecture": "architecture",
            "studio_type": "studio_type",
        }
        field_name = field_map.get(item_key)
        if not field_name:
            return False
        return getattr(self.config, field_name) != getattr(self.original_config, field_name)

    def _refresh_rows(self) -> None:
        for index, item in enumerate(self.items):
            widget = self.query_one(f"#row_{item.key}", Static)
            widget.update(self._render_row(item, index == self.focused_index))
            widget.remove_class("config-row-focused")
            if index == self.focused_index:
                widget.add_class("config-row-focused")
                widget.scroll_visible()

    def _refresh_detail(self) -> None:
        item = self.items[self.focused_index]
        widget = self.query_one("#detail", Static)
        widget.update(self._build_detail_text(item))
        self.query_one("#detail-scroll", ScrollableContainer).scroll_to(0, 0, animate=False)

    def _build_detail_text(self, item: ConfigItem) -> str:
        lines = [item.description, ""]

        if item.key == "architecture":
            selected = next(
                (option for option in self.architecture_options if option["value"] == self.config.architecture),
                None,
            )
            if selected:
                lines.append(f"当前架构: {selected['label']}")
                lines.append(selected["description"])
            lines.append("")
            lines.append("布局说明:")
            lines.append("- 中心化：主脑与专才各自独立工作区")
            lines.append("- 去中心化：团队成员共享同一工作区")
            lines.append("- 混合：主脑独立，专才共享团队工作区")
        elif item.key == "studio_type":
            template = get_template(self.config.studio_type)
            lines.append(f"当前模板: {template.name}")
            lines.append(template.description)
            lines.append("")
            lines.append("默认成员:")
            for agent in template.get_agents():
                role_flag = "[主脑] " if agent.is_main_brain else ""
                lines.append(f"- {agent.emoji} {agent.display_name}: {role_flag}{agent.role}")
        elif item.key == "save":
            lines.append("待保存摘要:")
            lines.extend(self._summary_lines())
            lines.append("")
            lines.append("保存后请执行: mushtech_studio reset")
            lines.append("reset 会重建 openclaw.json、重新创建 Agent，并向每个会话发送 /new。")
        elif item.key == "quit":
            lines.append("未保存修改: " + ("是" if self._has_unsaved_changes() else "否"))
        else:
            lines.append(f"当前值: {self._value_for_item(item)}")

        return "\n".join(lines)

    def _summary_lines(self) -> list[str]:
        return [
            f"- Gateway Token: {self._mask(self.config.gateway_token)}",
            f"- Gateway 地址: {self.config.gateway_host}:{self.config.gateway_port}",
            f"- Workspace: {self.config.base_workspace}",
            f"- 架构: {self.config.get_architecture_display_name()}",
            f"- 模板: {self.config.get_studio_type_display_name()}",
        ]

    def _show_message(self, message: str, is_error: bool = False) -> None:
        widget = self.query_one("#message", Static)
        prefix = "[错误] " if is_error else "[提示] "
        widget.update(prefix + message)

    def action_move_up(self) -> None:
        if self.focused_index > 0:
            self.focused_index -= 1

    def action_move_down(self) -> None:
        if self.focused_index < len(self.items) - 1:
            self.focused_index += 1

    def action_select(self) -> None:
        item = self.items[self.focused_index]

        if item.kind == "text":
            self._open_text_dialog(item)
            return

        if item.kind == "choice":
            self._open_choice_dialog(item)
            return

        if item.key == "save":
            self._save_config()
            return

        if item.key == "quit":
            self.app.exit()

    def _open_text_dialog(self, item: ConfigItem) -> None:
        value_map = {
            "token": self.config.gateway_token,
            "host": self.config.gateway_host,
            "port": str(self.config.gateway_port),
            "workspace": self.config.base_workspace,
        }

        def on_result(result: Optional[str]) -> None:
            if result is None:
                return

            new_value = result.strip()
            if item.key == "token":
                self.config.gateway_token = new_value
            elif item.key == "host":
                if not new_value:
                    self._show_message("Gateway IP 地址不能为空", True)
                    return
                self.config.gateway_host = new_value
            elif item.key == "port":
                try:
                    port = int(new_value)
                except ValueError:
                    self._show_message("Gateway 端口必须是数字", True)
                    return
                if not 1 <= port <= 65535:
                    self._show_message("Gateway 端口必须在 1-65535 之间", True)
                    return
                self.config.gateway_port = port
            elif item.key == "workspace":
                if not new_value:
                    self._show_message("Workspace 路径不能为空", True)
                    return
                self.config.base_workspace = new_value

            self._refresh_all()
            self._show_message(f"已更新 {item.label}")

        self.app.push_screen(
            TextInputDialog(item.label, item.description, value_map[item.key], item.is_password),
            on_result,
        )

    def _open_choice_dialog(self, item: ConfigItem) -> None:
        if item.key == "architecture":
            options = self.architecture_options
            current_value = self.config.architecture
        else:
            options = self.template_options
            current_value = self.config.studio_type

        def on_result(result: Optional[str]) -> None:
            if result is None:
                return
            if item.key == "architecture":
                self.config.architecture = result
                self._show_message(f"已切换架构为：{self.config.get_architecture_display_name()}")
            else:
                self.config.studio_type = result
                self._show_message(f"已切换模板为：{self.config.get_studio_type_display_name()}")
            self._refresh_all()

        self.app.push_screen(ChoiceDialog(item.label, item.description, options, current_value), on_result)

    def _validate_config(self) -> list[str]:
        errors = []
        if not self.config.gateway_host:
            errors.append("Gateway IP 地址不能为空")
        if not 1 <= int(self.config.gateway_port) <= 65535:
            errors.append("Gateway 端口必须在 1-65535 之间")
        if not self.config.base_workspace:
            errors.append("Workspace 路径不能为空")
        return errors

    def _save_config(self) -> None:
        errors = self._validate_config()
        if errors:
            self._show_message("；".join(errors), True)
            return

        summary = "\n".join(
            self._summary_lines()
            + [
                "",
                "保存后不会自动 reset。",
                "请继续执行 mushtech_studio reset 使配置真正生效。",
            ]
        )

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return

            success = self.config_mgr.update_config(
                gateway_token=self.config.gateway_token,
                gateway_host=self.config.gateway_host,
                gateway_port=self.config.gateway_port,
                base_workspace=self.config.base_workspace,
                architecture=self.config.architecture,
                studio_type=self.config.studio_type,
            )
            if not success:
                self._show_message("保存配置失败", True)
                return

            self.original_config = StudioConfig.from_dict(self.config.to_dict())
            self._refresh_all()
            self._show_message("配置已保存。请继续执行 mushtech_studio reset 以应用新配置。")

        self.app.push_screen(ConfirmSaveDialog(summary), on_confirm)

    def action_quit(self) -> None:
        self.app.exit()


class ConfigApp(App):
    """配置应用"""

    CSS = "Screen { background: black; }"

    def on_mount(self) -> None:
        self.push_screen(ConfigScreen())


def run_config_screen() -> None:
    app = ConfigApp()
    app.run()
