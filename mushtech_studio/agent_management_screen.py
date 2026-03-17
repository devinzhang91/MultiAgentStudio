#!/usr/bin/env python3
"""
智能体管理 - 极简设计
"""

from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical, Horizontal

from .agent_initializer import AgentInitializer
from .models import EmployeeStore, Employee, create_employee_from_agent_config
from .cmd_executor import get_cmd_executor
from .logger import logger
from .utils import pad_to_width


class AgentManagementScreen(Screen):
    """智能体管理主界面"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: 1 1 1fr 1;
        background: black;
    }
    
    #title {
        height: 1;
        background: black;
        color: green;
        text-style: bold;
        content-align: center middle;
        border-bottom: solid green;
    }
    
    #help {
        height: 1;
        background: darkgreen;
        color: black;
        text-style: bold;
        content-align: center middle;
    }
    
    #list {
        height: 100%;
        overflow-y: auto;
        border: solid green;
    }
    
    .header-row {
        height: 1;
        background: darkgreen;
        color: black;
        text-style: bold;
    }
    
    .item {
        height: 1;
        color: green;
    }
    
    .item.selected {
        background: green;
        color: black;
        text-style: bold;
    }
    
    #status {
        height: 1;
        background: black;
        color: green;
        border-top: solid green;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "返回"),
        ("a", "add", "添加"),
        ("d", "delete", "删除"),
        ("r", "refresh", "刷新"),
        ("enter", "edit", "编辑"),
        ("up", "up", "上"),
        ("down", "down", "下"),
    ]
    
    def __init__(self, store: EmployeeStore):
        super().__init__()
        self.store = store
        self.cmd = get_cmd_executor()
        self.initializer = AgentInitializer()
        self.employees = []
        self.selected = 0
    
    def compose(self):
        yield Static(" 🐠 智能体管理 ", id="title")
        yield Static(" ↑↓选 Enter编 A增 D删 R刷 ESC返 ", id="help")
        yield Vertical(id="list")
        yield Static(" 准备就绪", id="status")
    
    def on_mount(self):
        self._load_data()
    
    def _load_data(self):
        self.store.load()
        # 排序：主脑放在第一位，其他按id排序
        self.employees = sorted(
            self.store.employees.values(), 
            key=lambda e: (not e.is_main_brain, e.id)
        )
        
        list_container = self.query_one("#list", Vertical)
        list_container.remove_children()
        
        # 表头 - 使用对齐函数
        header_parts = [
            pad_to_width("员工ID", 12),
            pad_to_width("Agent ID", 14),
            pad_to_width("显示名", 12),
            pad_to_width("角色", 22),
            pad_to_width("类型", 6),
        ]
        header_line = " " + "  ".join(header_parts)
        list_container.mount(Static(header_line, classes="header-row"))
        
        # 数据行 - 使用对齐函数
        for i, emp in enumerate(self.employees):
            name = emp.display_name or emp.name
            typ = "主脑" if emp.is_main_brain else "专才"
            
            row_parts = [
                pad_to_width(emp.id[:12], 12),
                pad_to_width(emp.agent_id[:14], 14),
                pad_to_width(name[:12], 12),
                pad_to_width(emp.role[:22], 22),
                pad_to_width(typ, 6),
            ]
            line = " " + "  ".join(row_parts)
            item = Static(line, classes="item selected" if i == 0 else "item")
            list_container.mount(item)
        
        self.selected = 0
        self._update_status(f"共 {len(self.employees)} 个智能体")
    
    def _update_selection(self):
        items = list(self.query(".item"))
        for i, item in enumerate(items):
            item.classes = "item selected" if i == self.selected else "item"
    
    def _update_status(self, msg):
        self.query_one("#status", Static).update(f" {msg}")
    
    def _get_selected_emp(self):
        if 0 <= self.selected < len(self.employees):
            return self.employees[self.selected]
        return None
    
    def action_up(self):
        if self.selected > 0:
            self.selected -= 1
            self._update_selection()
    
    def action_down(self):
        if self.selected < len(self.employees) - 1:
            self.selected += 1
            self._update_selection()
    
    def action_refresh(self):
        self._load_data()
    
    def action_back(self):
        self.app.pop_screen()
    
    def action_edit(self):
        emp = self._get_selected_emp()
        if emp:
            self.app.push_screen(EditAgentScreen(self.store, emp), self._on_edit_done)
    
    def _on_edit_done(self, result):
        if result:
            self.run_worker(self._do_update(result))
    
    async def _do_update(self, data):
        try:
            emp = self.store.employees.get(data["emp_id"])
            if not emp:
                return
            
            self.store.update(
                data["emp_id"],
                agent_id=data["agent_id"],
                name=data["name"],
                display_name=data["display_name"],
                role=data["role"],
                model=data["model"],
                workspace=data["workspace"],
                emoji=data["emoji"],
            )
            
            self.cmd.agents_set_identity(
                emp.agent_id,
                name=data["display_name"] or data["name"],
                emoji=data["emoji"]
            )
            
            self._load_data()
            self.notify("✅ 已保存")
        except Exception as e:
            logger.exception(f"更新失败: {e}")
            self.notify(f"❌ 失败: {e}", severity="error")
    
    def action_add(self):
        self.app.push_screen(AddAgentScreen(self.store), self._on_add_done)
    
    def _on_add_done(self, result):
        if result:
            self.run_worker(self._do_add(result))
    
    async def _do_add(self, data):
        try:
            emp_id = f"emp-{data['agent_id'].replace('_', '-')}"
            if emp_id in self.store.employees:
                self.notify("❌ 已存在", severity="error")
                return
            
            emp = create_employee_from_agent_config(
                agent_id=data["agent_id"],
                name=data["name"],
                role=data["role"],
                workspace=f"{self.store.multi_agent_config.base_workspace}/workspace-{data['agent_id']}",
                model=data.get("model", "volcengine/glm-4.7"),
                is_main_brain=False,
                allowed_tools=[],
                emoji=data.get("emoji", "💼"),
            )
            emp.id = emp_id
            emp.display_name = data.get("display_name", data["name"])
            
            success, _ = self.cmd.agents_add(
                name=emp.agent_id,
                workspace=emp.workspace,
                agent_dir=emp.agent_dir,
                model=emp.model,
                non_interactive=True
            )
            
            if success:
                self.cmd.agents_set_identity(emp.agent_id, name=emp.display_name or emp.name, emoji=emp.emoji)
                self.store.add(emp)
                bootstrap_ok, bootstrap_reason = self.initializer.initialize_employee(emp, reset_after_bootstrap=True)
                self._load_data()
                if bootstrap_ok:
                    self.notify("✅ 已创建并初始化")
                else:
                    self.notify(f"⚠️ 已创建，但初始化失败: {bootstrap_reason}", severity="warning")
            else:
                self.notify("❌ 创建失败", severity="error")
        except Exception as e:
            logger.exception(f"创建失败: {e}")
            self.notify(f"❌ 失败: {e}", severity="error")
    
    def action_delete(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        
        if emp.is_main_brain:
            brains = [e for e in self.store.employees.values() if e.is_main_brain]
            if len(brains) <= 1:
                self.notify("❌ 不能删除唯一主脑", severity="error")
                return
        
        self.app.push_screen(
            ConfirmDialog(f"删除 '{emp.name}'?"),
            lambda ok: self._on_delete_confirm(ok, emp) if ok else None
        )
    
    def _on_delete_confirm(self, ok, emp):
        if ok:
            self.run_worker(self._do_delete(emp))
    
    async def _do_delete(self, emp):
        try:
            self.store.delete(emp.id)
            self.cmd.agents_delete(emp.agent_id, force=True)
            self._load_data()
            self.notify("✅ 已删除")
        except Exception as e:
            logger.exception(f"删除失败: {e}")
            self.notify(f"❌ 失败: {e}", severity="error")


class EditAgentScreen(Screen):
    """编辑智能体 - 使用↑↓选择和Enter弹出编辑框"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: 1 1 1fr 1;
        background: black;
    }
    
    #edit-title {
        height: 1;
        background: green;
        color: black;
        text-style: bold;
        content-align: center middle;
    }
    
    #edit-help {
        height: 1;
        background: darkgreen;
        color: black;
        text-style: bold;
        content-align: center middle;
    }
    
    #edit-form {
        height: 100%;
        overflow-y: auto;
        padding: 0 4;
    }
    
    .field-row {
        height: 1;
        padding: 0 1;
        color: green;
    }
    
    .field-row.selected {
        background: green;
        color: black;
        text-style: bold;
    }
    
    .field-row.readonly {
        color: gray;
    }
    
    #edit-status {
        height: 1;
        background: black;
        color: green;
        border-top: solid green;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("s", "save", "保存"),
        ("up", "move_up", "上"),
        ("down", "move_down", "下"),
        ("enter", "edit_field", "编辑"),
    ]
    
    # 字段定义: (字段名, 标签, 是否可编辑, 列宽)
    FIELDS = [
        ("emp_id", "员工ID", False, 12),
        ("agent_id", "Agent ID", True, 12),
        ("name", "姓名", True, 12),
        ("display_name", "显示名", True, 12),
        ("role", "角色", True, 20),
        ("model", "模型", True, 20),
        ("workspace", "工作区", True, 30),
        ("emoji", "Emoji", True, 8),
    ]
    
    def __init__(self, store: EmployeeStore, emp: Employee):
        super().__init__()
        self.store = store
        self.emp = emp
        self.values = {}
        self.focused_index = 0
        self.field_rows = []
    
    def compose(self):
        yield Static(f" ✏️ 编辑: {self.emp.name} ", id="edit-title")
        yield Static(" ↑↓选择 Enter编辑 S保存 ESC取消 ", id="edit-help")
        
        with Vertical(id="edit-form"):
            for field, label, editable, value_width in self.FIELDS:
                value = getattr(self.emp, field, "") or ""
                self.values[field] = value
                
                row_classes = "field-row"
                if not editable:
                    row_classes += " readonly"
                
                # 格式化显示: 标签(固定12宽) + 值(根据字段不同)
                display_value = value if value else "(空)"
                label_str = pad_to_width(label, 12)
                value_str = pad_to_width(display_value, value_width)
                line = f" {label_str}  {value_str}"
                
                row = Static(line, classes=row_classes)
                row.field_name = field
                row.field_label = label
                row.editable = editable
                self.field_rows.append(row)
                yield row
        
        yield Static(" 选择字段并按Enter编辑", id="edit-status")
    
    def on_mount(self):
        self.focused_index = 0
        self._update_selection()
    
    def _update_selection(self):
        """更新选中状态"""
        for i, row in enumerate(self.field_rows):
            if i == self.focused_index:
                row.add_class("selected")
            else:
                row.remove_class("selected")
        
        # 更新状态栏
        field, label, editable, _ = self.FIELDS[self.focused_index]
        if editable:
            self.query_one("#edit-status", Static).update(f" 选中: {label}  [Enter]编辑 [↑↓]移动 [S]保存")
        else:
            self.query_one("#edit-status", Static).update(f" 选中: {label}  只读  [↑↓]移动")
    
    def action_move_up(self):
        if self.focused_index > 0:
            self.focused_index -= 1
            self._update_selection()
    
    def action_move_down(self):
        if self.focused_index < len(self.FIELDS) - 1:
            self.focused_index += 1
            self._update_selection()
    
    def action_edit_field(self):
        """编辑当前选中的字段"""
        field, label, editable, _ = self.FIELDS[self.focused_index]
        if not editable:
            return
        
        current_value = self.values[field]
        self.app.push_screen(
            EditFieldDialog(label, current_value),
            lambda result: self._on_field_edit(result, field)
        )
    
    def _on_field_edit(self, result, field):
        """字段编辑完成回调"""
        if result is not None:
            self.values[field] = result
            self._refresh_field_display()
    
    def _refresh_field_display(self):
        """刷新字段显示"""
        for i, (field, label, editable, value_width) in enumerate(self.FIELDS):
            value = self.values[field]
            display_value = value if value else "(空)"
            label_str = pad_to_width(label, 12)
            value_str = pad_to_width(display_value, value_width)
            line = f" {label_str}  {value_str}"
            self.field_rows[i].update(line)
    
    def action_save(self):
        """保存所有更改"""
        data = {
            "emp_id": self.values["emp_id"],
            "agent_id": self.values["agent_id"].strip(),
            "name": self.values["name"].strip(),
            "display_name": self.values["display_name"].strip(),
            "role": self.values["role"].strip(),
            "model": self.values["model"].strip(),
            "workspace": self.values["workspace"].strip(),
            "emoji": self.values["emoji"].strip(),
        }
        
        if not data["agent_id"] or not data["name"]:
            self.query_one("#edit-status", Static).update(" ❌ Agent ID和姓名不能为空")
            return
        
        self.dismiss(data)
    
    def action_cancel(self):
        self.dismiss(None)


class EditFieldDialog(ModalScreen):
    """编辑单个字段的对话框"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    #dialog-box {
        width: 60;
        height: auto;
        background: black;
        border: solid cyan;
        padding: 2;
    }
    
    #dialog-label {
        height: 1;
        color: cyan;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #dialog-input {
        width: 100%;
        height: 3;
        background: black;
        color: cyan;
        border: solid cyan;
    }
    
    #dialog-input:focus {
        background: cyan;
        color: black;
        border: solid cyan;
    }
    
    #dialog-help {
        height: 1;
        background: darkgreen;
        color: black;
        text-style: bold;
        content-align: center middle;
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "取消"),
    ]
    
    def __init__(self, label: str, current_value: str):
        super().__init__()
        self.label = label
        self.current_value = current_value
    
    def compose(self):
        with Vertical(id="dialog-box"):
            yield Static(f"编辑: {self.label}", id="dialog-label")
            
            inp = Input(value=self.current_value, id="dialog-input")
            yield inp
            
            yield Static(" ⏎ Enter确认  ⎋ Esc取消", id="dialog-help")
    
    def on_mount(self):
        """挂载后聚焦输入框并全选"""
        inp = self.query_one("#dialog-input", Input)
        inp.focus()
        inp.action_select_all()
    
    def on_input_submitted(self, event: Input.Submitted):
        """输入框提交（按Enter）"""
        self.dismiss(event.value)
    
    def action_cancel(self):
        self.dismiss(None)


class AddAgentScreen(Screen):
    """添加智能体 - 使用↑↓选择和Enter弹出编辑框"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: 1 1 1fr 1;
        background: black;
    }
    
    #add-title {
        height: 1;
        background: cyan;
        color: black;
        text-style: bold;
        content-align: center middle;
    }
    
    #add-help {
        height: 1;
        background: darkcyan;
        color: black;
        text-style: bold;
        content-align: center middle;
    }
    
    #add-form {
        height: 100%;
        overflow-y: auto;
        padding: 0 4;
    }
    
    .field-row {
        height: 1;
        padding: 0 1;
        color: cyan;
    }
    
    .field-row.selected {
        background: cyan;
        color: black;
        text-style: bold;
    }
    
    #add-status {
        height: 1;
        background: black;
        color: cyan;
        border-top: solid cyan;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("s", "save", "保存"),
        ("up", "move_up", "上"),
        ("down", "move_down", "下"),
        ("enter", "edit_field", "编辑"),
    ]
    
    # 字段定义: (字段名, 标签, 默认值)
    FIELDS = [
        ("agent_id", "Agent ID", ""),
        ("name", "姓名", ""),
        ("display_name", "显示名", ""),
        ("role", "角色", ""),
        ("model", "模型", "volcengine/glm-4.7"),
        ("emoji", "Emoji", "💼"),
    ]
    
    def __init__(self, store: EmployeeStore):
        super().__init__()
        self.store = store
        self.values = {}
        self.focused_index = 0
        self.field_rows = []
    
    def compose(self):
        yield Static(" ➕ 添加新智能体 ", id="add-title")
        yield Static(" ↑↓选择 Enter编辑 S保存 ESC取消 ", id="add-help")
        
        with Vertical(id="add-form"):
            for field, label, default in self.FIELDS:
                self.values[field] = default
                
                display_value = default if default else "(空)"
                line = f" {label:<12} │ {display_value}"
                
                row = Static(line, classes="field-row")
                row.field_name = field
                row.field_label = label
                self.field_rows.append(row)
                yield row
        
        yield Static(" 选择字段并按Enter编辑", id="add-status")
    
    def on_mount(self):
        self.focused_index = 0
        self._update_selection()
    
    def _update_selection(self):
        """更新选中状态"""
        for i, row in enumerate(self.field_rows):
            if i == self.focused_index:
                row.add_class("selected")
            else:
                row.remove_class("selected")
        
        # 更新状态栏
        field, label, _ = self.FIELDS[self.focused_index]
        self.query_one("#add-status", Static).update(f" 选中: {label} │ [Enter]编辑 [↑↓]移动 [S]保存")
    
    def action_move_up(self):
        if self.focused_index > 0:
            self.focused_index -= 1
            self._update_selection()
    
    def action_move_down(self):
        if self.focused_index < len(self.FIELDS) - 1:
            self.focused_index += 1
            self._update_selection()
    
    def action_edit_field(self):
        """编辑当前选中的字段"""
        field, label, _ = self.FIELDS[self.focused_index]
        current_value = self.values[field]
        
        self.app.push_screen(
            EditFieldDialog(label, current_value),
            lambda result: self._on_field_edit(result, field)
        )
    
    def _on_field_edit(self, result, field):
        """字段编辑完成回调"""
        if result is not None:
            self.values[field] = result
            self._refresh_field_display()
    
    def _refresh_field_display(self):
        """刷新字段显示"""
        for i, (field, label, _) in enumerate(self.FIELDS):
            value = self.values[field]
            display_value = value if value else "(空)"
            line = f" {label:<12} │ {display_value}"
            self.field_rows[i].update(line)
    
    def action_save(self):
        """保存"""
        data = {
            "agent_id": self.values["agent_id"].strip(),
            "name": self.values["name"].strip(),
            "display_name": self.values["display_name"].strip(),
            "role": self.values["role"].strip(),
            "model": self.values["model"].strip(),
            "emoji": self.values["emoji"].strip(),
        }
        
        if not data["agent_id"] or not data["name"]:
            self.query_one("#add-status", Static).update(" ❌ Agent ID和姓名不能为空")
            return
        
        self.dismiss(data)
    
    def action_cancel(self):
        self.dismiss(None)


class ConfirmDialog(ModalScreen):
    """确认对话框"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    #box {
        width: 50;
        height: auto;
        background: black;
        border: solid yellow;
        padding: 2;
    }
    
    #msg {
        height: auto;
        color: yellow;
        text-align: center;
        margin-bottom: 1;
    }
    
    #btns {
        height: 3;
    }
    
    Button {
        width: 1fr;
        background: black;
        border: solid yellow;
        color: yellow;
    }
    
    Button:focus {
        background: yellow;
        color: black;
    }
    """
    
    BINDINGS = [("y", "yes", "是"), ("n", "no", "否"), ("escape", "no", "否")]
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self):
        with Vertical(id="box"):
            yield Static(self.message, id="msg")
            with Horizontal(id="btns"):
                yield Button("是 (Y)", id="yes")
                yield Button("否 (N)", id="no")
    
    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "yes")
    
    def action_yes(self):
        self.dismiss(True)
    
    def action_no(self):
        self.dismiss(False)
