"""
添加员工界面 - 键盘驱动表单
"""

from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical, Horizontal

from .models import Employee
from .logger import logger


class AddEmployeeScreen(ModalScreen):
    """添加员工对话框 - 纯键盘操作"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    .modal-container {
        width: 60;
        height: auto;
        background: black;
        border: solid green;
        padding: 1 2;
    }
    .modal-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: green;
    }
    .form-row {
        height: 3;
        margin: 1 0;
    }
    .form-label {
        width: 12;
        color: green;
    }
    .form-input {
        width: 1fr;
        background: black;
        color: green;
        border: solid green;
    }
    .form-hint {
        color: darkgray;
        text-style: italic;
    }
    .button-row {
        height: 3;
        margin-top: 1;
    }
    .btn {
        width: 1fr;
        background: black;
        color: green;
        border: solid green;
    }
    .btn:focus {
        background: green;
        color: black;
    }
    .btn-primary {
        background: green;
        color: black;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("tab", "next_field", "下一个"),
        ("shift+tab", "prev_field", "上一个"),
    ]
    
    def __init__(self):
        super().__init__()
        self.result = None
        logger.debug("AddEmployeeScreen initialized")
    
    def compose(self):
        logger.debug("AddEmployeeScreen composing UI")
        with Vertical(classes="modal-container"):
            yield Static("🦞 添加新员工", classes="modal-title")
            
            with Horizontal(classes="form-row"):
                yield Static("ID:", classes="form-label")
                yield Input(
                    placeholder="emp-004",
                    id="input-id",
                    classes="form-input"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("名称:", classes="form-label")
                yield Input(
                    placeholder="员工名称",
                    id="input-name",
                    classes="form-input"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("角色:", classes="form-label")
                yield Input(
                    placeholder="如: 代码助手",
                    id="input-role",
                    classes="form-input"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("Session:", classes="form-label")
                yield Input(
                    placeholder="OpenClaw session key",
                    id="input-session",
                    classes="form-input"
                )
            yield Static("  用于区分 OpenClaw 中的会话", classes="form-hint")
            
            with Horizontal(classes="button-row"):
                btn_ok = Button("✓ 确认 (Enter)", id="btn-ok", classes="btn btn-primary")
                btn_cancel = Button("✗ 取消 (ESC)", id="btn-cancel", classes="btn")
                btn_ok.can_focus = True
                btn_cancel.can_focus = True
                yield btn_ok
                yield btn_cancel
    
    def on_mount(self):
        """初始化焦点"""
        logger.debug("AddEmployeeScreen mounted")
        self.query_one("#input-id", Input).focus()
    
    def on_input_submitted(self, event: Input.Submitted):
        """输入框提交时切换到下一个或确认"""
        current_id = event.input.id
        logger.debug(f"Input submitted: {current_id}")
        if current_id == "input-id":
            self.query_one("#input-name", Input).focus()
        elif current_id == "input-name":
            self.query_one("#input-role", Input).focus()
        elif current_id == "input-role":
            self.query_one("#input-session", Input).focus()
        elif current_id == "input-session":
            self._confirm()
    
    def on_button_pressed(self, event: Button.Pressed):
        """按钮点击"""
        logger.info(f"Button pressed: {event.button.id}")
        if event.button.id == "btn-ok":
            self._confirm()
        else:
            self._cancel()
    
    def _confirm(self):
        """确认添加"""
        emp_id = self.query_one("#input-id", Input).value.strip()
        name = self.query_one("#input-name", Input).value.strip()
        role = self.query_one("#input-role", Input).value.strip()
        session = self.query_one("#input-session", Input).value.strip()
        
        logger.info(f"Confirming add: id={emp_id}, name={name}, role={role}, session={session}")
        
        # 验证
        if not emp_id:
            logger.warning("Validation failed: ID is empty")
            self.notify("ID 不能为空", severity="error")
            self.query_one("#input-id", Input).focus()
            return
        if not name:
            logger.warning("Validation failed: name is empty")
            self.notify("名称不能为空", severity="error")
            self.query_one("#input-name", Input).focus()
            return
        
        # 生成 session_key（如果没有提供）
        if not session:
            session = name.lower().replace(" ", "-")
            logger.debug(f"Generated session key: {session}")
        
        # 创建员工对象
        self.result = Employee(
            id=emp_id,
            name=name,
            role=role or "OpenClaw 员工",
            config={"session_key": session}
        )
        
        logger.info(f"Employee created: {emp_id} ({name})")
        self.dismiss(self.result)
    
    def _cancel(self):
        """取消"""
        logger.info("Add employee cancelled")
        self.result = None
        self.dismiss(None)
    
    def action_cancel(self):
        """ESC 取消"""
        self._cancel()
    
    def action_next_field(self):
        """Tab 切换下一个"""
        self.screen.focus_next()
    
    def action_prev_field(self):
        """Shift+Tab 切换上一个"""
        self.screen.focus_previous()
