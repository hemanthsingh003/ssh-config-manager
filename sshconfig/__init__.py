from enum import Enum
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static, Input, Button, ListView, ListItem

from .config import SSHConfigParser, SSHHost
from .vault import PasswordVault
from .utils import UsageTracker, test_connection, copy_to_clipboard, backup_config


class SortMode(Enum):
    NAME = "name"
    LAST_MODIFIED = "last_modified"
    LAST_USED = "last_used"


class SSHConfigApp(App):
    CSS = """
    Screen {
        background: #1a1a1a;
    }

    #header {
        height: 2;
        background: #2d2d2d;
        color: #e0e0e0;
        text-align: center;
    }

    #footer {
        height: 2;
        background: #2d2d2d;
        dock: bottom;
    }

    #footer Static {
        text-align: center;
        color: #a0a0a0;
    }

    #main {
        height: 1fr;
    }

    #left-panel {
        width: 35%;
        background: #1e1e1e;
    }

    #right-panel {
        width: 65%;
        background: #252525;
        border-left: solid #3d3d3d;
    }

    #search-input {
        width: 100%;
        margin: 1;
    }

    #host-list {
        height: 100%;
        background: #1e1e1e;
        border: none;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:hover {
        background: #3d3d3d;
    }

    #detail-title {
        height: 3;
        background: #2d2d2d;
        color: #ffffff;
        text-style: bold;
    }

    #detail-content {
        padding: 2;
        color: #c0c0c0;
    }

    .detail-label {
        text-style: bold;
        color: #ffffff;
    }

    .detail-value {
        color: #a0a0a0;
    }

    #status-msg {
        height: 1;
        padding: 0 1;
        color: #4caf50;
        background: #2d2d2d;
    }

    #form-container {
        display: none;
        padding: 2;
        width: 100%;
        height: 100%;
    }

    #form-container.visible {
        display: block;
    }

    #form-title {
        height: 3;
        background: #2d2d2d;
        color: #ffffff;
        text-style: bold;
    }

    .form-field {
        height: 3;
        width: 100%;
    }

    .form-field > Static {
        width: 20;
        color: #e0e0e0;
    }

    .form-field > Input {
        width: 1fr;
        background: #3d3d3d;
        color: #e0e0e0;
    }

    #form-buttons {
        height: 3;
        margin-top: 1;
    }

    #btn-save {
        margin-right: 1;
    }

    Input {
        background: #3d3d3d;
        color: #e0e0e0;
    }

    Button {
        background: #4a4a4a;
    }

    Button:hover {
        background: #5a5a5a;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False, priority=True),
        Binding("j", "cursor_down", "Down", show=False, priority=True),
        Binding("k", "cursor_up", "Up", show=False, priority=True),
        Binding("g", "goto_top", "Top", show=False, priority=True),
        Binding("G", "goto_bottom", "Bottom", show=False, priority=True),
        Binding("/", "focus_search", "Search", show=False, priority=True),
        Binding("n", "sort_by_name", "Sort by name", show=False, priority=True),
        Binding("m", "sort_by_modified", "Sort by modified", show=False, priority=True),
        Binding("u", "sort_by_used", "Sort by used", show=False, priority=True),
        Binding("a", "add_host", "Add host", show=False, priority=True),
        Binding("e", "edit_host", "Edit host", show=False, priority=True),
        Binding("d", "delete_host", "Delete host", show=False, priority=True),
        Binding("y", "yank_host", "Yank host", show=False, priority=True),
        Binding("c", "copy_ssh_command", "Copy SSH", show=False, priority=True),
        Binding("P", "copy_ssh_with_password", "Copy SSH+pass", show=False, priority=True),
        Binding("t", "test_connection", "Test", show=False, priority=True),
        Binding("escape", "cancel_or_close_form", "Cancel", show=False, priority=True),
        Binding("enter", "activate_focused_button", "Activate", show=False, priority=True),
        Binding("?", "show_help", "Help", show=False, priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.parser = SSHConfigParser()
        self.vault = PasswordVault()
        self.tracker = UsageTracker()
        self.hosts: list[SSHHost] = []
        self.filtered_hosts: list[SSHHost] = []
        self.selected_index = 0
        self.sort_mode = SortMode.NAME
        self.search_query = ""
        self.current_view = "list"
        self.vault_unlocked = False
        self.form_visible = False
        self.editing_host: Optional[SSHHost] = None

    def compose(self) -> ComposeResult:
        yield Static(" SSH Config Manager ", id="header")
        with Horizontal(id="main"):
            with Vertical(id="left-panel"):
                yield Input(placeholder="Search... (press /)", id="search-input")
                yield ListView(id="host-list")
            with Vertical(id="right-panel"):
                yield Static(" Config Details ", id="detail-title")
                yield Static("", id="detail-content")
                with Vertical(id="form-container"):
                    yield Static(" Add / Edit Host ", id="form-title")
                    with Horizontal(classes="form-field"):
                        yield Static("Host: ")
                        yield Input("", id="form-name")
                    with Horizontal(classes="form-field"):
                        yield Static("Hostname: ")
                        yield Input("", id="form-hostname")
                    with Horizontal(classes="form-field"):
                        yield Static("User: ")
                        yield Input("", id="form-user")
                    with Horizontal(classes="form-field"):
                        yield Static("Port: ")
                        yield Input("22", id="form-port")
                    with Horizontal(classes="form-field"):
                        yield Static("Identity: ")
                        yield Input("", id="form-identity")
                    with Horizontal(classes="form-field"):
                        yield Static("ProxyJump: ")
                        yield Input("", id="form-proxy")
                    with Horizontal(classes="form-field"):
                        yield Static("Password: ")
                        yield Input("", id="form-password", password=True)
                    with Horizontal(id="form-buttons"):
                        yield Button("Save", id="btn-save", variant="primary")
                        yield Button("Cancel", id="btn-cancel")
        yield Static("", id="status-msg")
        yield Static(" vim-like: j/k=navigate  /=search  a=add  e=edit  d=delete  y=yank  c=copy  P=sshpass  t=test  n/m/u=sort  Esc=cancel  q=quit  ?=help ", id="footer")

    def on_mount(self) -> None:
        self.load_hosts()
        self.refresh_list()
        list_view = self.query_one("#host-list", ListView)
        list_view.focus()

    def load_hosts(self) -> None:
        self.hosts = self.parser.parse()
        self._apply_sort()
        self._apply_filter()

    def _apply_sort(self) -> None:
        if self.sort_mode == SortMode.NAME:
            self.hosts.sort(key=lambda h: h.name.lower())
        elif self.sort_mode == SortMode.LAST_MODIFIED:
            def get_modified(h: SSHHost) -> float:
                usage = self.tracker.get_usage(h.name)
                return usage.last_modified if usage else 0
            self.hosts.sort(key=get_modified, reverse=True)
        elif self.sort_mode == SortMode.LAST_USED:
            def get_used(h: SSHHost) -> float:
                usage = self.tracker.get_usage(h.name)
                return usage.last_used if usage else 0
            self.hosts.sort(key=get_used, reverse=True)

    def _apply_filter(self) -> None:
        if self.search_query:
            self.filtered_hosts = self.parser.search(self.search_query, self.hosts)
        else:
            self.filtered_hosts = self.hosts.copy()

    def refresh_list(self) -> None:
        list_view = self.query_one("#host-list", ListView)
        list_view.clear()
        for host in self.filtered_hosts:
            info = f"{host.user}@{host.hostname}" if host.hostname else "No hostname"
            if host.port and host.port != 22:
                info += f":{host.port}"
            list_view.append(
                ListItem(Static(f"[b]{host.name}[/b]  [dim]{info}[/dim]"))
            )
        if self.filtered_hosts:
            list_view.index = min(self.selected_index, len(self.filtered_hosts) - 1)
        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        if self.form_visible:
            return
        
        host = self.get_selected_host()
        detail_content = self.query_one("#detail-content", Static)
        
        if not host:
            detail_content.update("")
            return

        lines = []
        lines.append(f"[b white]Host:[/b white] [cyan]{host.name}[/cyan]")
        if host.hostname:
            lines.append(f"[b white]Hostname:[/b white] [gray]{host.hostname}[/gray]")
        if host.user:
            lines.append(f"[b white]User:[/b white] [gray]{host.user}[/gray]")
        if host.port:
            lines.append(f"[b white]Port:[/b white] [gray]{host.port}[/gray]")
        if host.identity_file:
            lines.append(f"[b white]IdentityFile:[/b white] [gray]{host.identity_file}[/gray]")
        if host.proxy_jump:
            lines.append(f"[b white]ProxyJump:[/b white] [gray]{host.proxy_jump}[/gray]")
        if host.forward_agent:
            lines.append("[b white]ForwardAgent:[/b white] [gray]yes[/gray]")
        if host.server_alive_interval:
            lines.append(f"[b white]ServerAliveInterval:[/b white] [gray]{host.server_alive_interval}[/gray]")
        if host.strict_host_key_checking:
            lines.append(f"[b white]StrictHostKeyChecking:[/b white] [gray]{host.strict_host_key_checking}[/gray]")
        
        has_password = False
        if self.vault.can_store_password():
            try:
                has_password = bool(self.vault.get_password(host.name))
            except ValueError:
                pass
        lines.append(f"[b white]Password:[/b white] [gray]{'stored' if has_password else 'not set'}[/gray]")
        
        if host.options:
            lines.append("")
            lines.append("[b white]Other options:[/b white]")
            for k, v in host.options.items():
                lines.append(f"  [gray]{k}[/gray]: [gray]{v}[/gray]")

        ssh_cmd = host.to_ssh_command()
        lines.append("")
        lines.append("[b white]SSH Command:[/b white]")
        lines.append(f"[green]{ssh_cmd}[/green]")

        config_str = host.to_config_string()
        lines.append("")
        lines.append("[b white]Full Config:[/b white]")
        lines.append(f"[dim]{config_str}[/dim]")

        detail_content.update("\n".join(lines))

    def get_selected_host(self) -> Optional[SSHHost]:
        if 0 <= self.selected_index < len(self.filtered_hosts):
            return self.filtered_hosts[self.selected_index]
        return None

    def show_status(self, message: str, is_error: bool = False) -> None:
        status = self.query_one("#status-msg", Static)
        status.update(message)
        if is_error:
            status.styles.color = "red"
        else:
            status.styles.color = "green"

    def action_cursor_down(self) -> None:
        if self.form_visible:
            return
        list_view = self.query_one("#host-list", ListView)
        if not self.filtered_hosts:
            return
        current_index = list_view.index or 0
        if current_index < len(self.filtered_hosts) - 1:
            list_view.index = current_index + 1
            self.selected_index = list_view.index
        else:
            list_view.index = 0
            self.selected_index = 0
        self._update_detail_panel()

    def action_cursor_up(self) -> None:
        if self.form_visible:
            return
        list_view = self.query_one("#host-list", ListView)
        if not self.filtered_hosts:
            return
        current_index = list_view.index or 0
        if current_index > 0:
            list_view.index = current_index - 1
            self.selected_index = list_view.index
        else:
            list_view.index = len(self.filtered_hosts) - 1
            self.selected_index = list_view.index
        self._update_detail_panel()

    def action_goto_top(self) -> None:
        if self.form_visible:
            return
        list_view = self.query_one("#host-list", ListView)
        list_view.index = 0
        self.selected_index = 0
        self._update_detail_panel()

    def action_goto_bottom(self) -> None:
        if self.form_visible:
            return
        list_view = self.query_one("#host-list", ListView)
        list_view.index = len(self.filtered_hosts) - 1
        self.selected_index = list_view.index
        self._update_detail_panel()

    def action_focus_search(self) -> None:
        if self.form_visible:
            return
        self.current_view = "search"
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_query = event.value
            self._apply_filter()
            self.refresh_list()

    def action_sort_by_name(self) -> None:
        if self.form_visible:
            return
        self.sort_mode = SortMode.NAME
        self._apply_sort()
        self._apply_filter()
        self.refresh_list()
        self.show_status("Sorted by name")

    def action_sort_by_modified(self) -> None:
        if self.form_visible:
            return
        self.sort_mode = SortMode.LAST_MODIFIED
        self._apply_sort()
        self._apply_filter()
        self.refresh_list()
        self.show_status("Sorted by last modified")

    def action_sort_by_used(self) -> None:
        if self.form_visible:
            return
        self.sort_mode = SortMode.LAST_USED
        self._apply_sort()
        self._apply_filter()
        self.refresh_list()
        self.show_status("Sorted by last used")

    def _show_form(self, host: Optional[SSHHost] = None) -> None:
        self.form_visible = True
        self.editing_host = host
        
        detail_title = self.query_one("#detail-title", Static)
        detail_content = self.query_one("#detail-content", Static)
        form_container = self.query_one("#form-container", Vertical)
        
        title = " Edit Host " if host else " Add Host "
        detail_title.update(title)
        detail_content.display = False
        form_container.add_class("visible")
        
        name_input = self.query_one("#form-name", Input)
        hostname_input = self.query_one("#form-hostname", Input)
        user_input = self.query_one("#form-user", Input)
        port_input = self.query_one("#form-port", Input)
        identity_input = self.query_one("#form-identity", Input)
        proxy_input = self.query_one("#form-proxy", Input)
        password_input = self.query_one("#form-password", Input)
        
        if host:
            name_input.value = host.name or ""
            hostname_input.value = host.hostname or ""
            user_input.value = host.user or ""
            port_input.value = str(host.port) if host.port else "22"
            identity_input.value = host.identity_file or ""
            proxy_input.value = host.proxy_jump or ""
            
            password_val = ""
            if host.name and self.vault.can_store_password():
                try:
                    password_val = self.vault.get_password(host.name) or ""
                except ValueError:
                    pass
            password_input.value = password_val
        else:
            name_input.value = ""
            hostname_input.value = ""
            user_input.value = ""
            port_input.value = "22"
            identity_input.value = ""
            proxy_input.value = ""
            password_input.value = ""
        
        name_input.focus()

    def _hide_form(self) -> None:
        self.form_visible = False
        self.editing_host = None
        
        detail_title = self.query_one("#detail-title", Static)
        detail_content = self.query_one("#detail-content", Static)
        form_container = self.query_one("#form-container", Vertical)
        
        detail_title.update(" Config Details ")
        detail_content.display = True
        form_container.remove_class("visible")
        
        self._update_detail_panel()
        
        list_view = self.query_one("#host-list", ListView)
        list_view.focus()

    def _submit_form(self) -> None:
        name_input = self.query_one("#form-name", Input)
        name = name_input.value.strip()
        
        if not name:
            self.show_status("Host name is required", is_error=True)
            name_input.focus()
            return
        
        hostname_input = self.query_one("#form-hostname", Input)
        user_input = self.query_one("#form-user", Input)
        port_input = self.query_one("#form-port", Input)
        identity_input = self.query_one("#form-identity", Input)
        proxy_input = self.query_one("#form-proxy", Input)
        password_input = self.query_one("#form-password", Input)
        
        hostname = hostname_input.value or None
        user = user_input.value or None
        port_str = port_input.value
        port = int(port_str) if port_str.isdigit() else 22
        identity_file = identity_input.value or None
        proxy_jump = proxy_input.value or None
        password = password_input.value or None
        
        host = SSHHost(
            name=name,
            hostname=hostname,
            user=user,
            port=port,
            identity_file=identity_file,
            proxy_jump=proxy_jump,
        )
        
        backup_config(self.parser.config_path)
        existing = self.parser.get_host(name)
        
        if existing and self.editing_host:
            self.parser.update_host(name, host)
            self.show_status(f"Updated host: {name}")
        else:
            self.parser.add_host(host)
            self.show_status(f"Added host: {name}")
        
        if password:
            try:
                self.vault.set_password(name, password)
            except ValueError:
                pass
        
        self.tracker.mark_modified(name)
        self.load_hosts()
        self._hide_form()
        self.refresh_list()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.form_visible:
            if event.button.id == "btn-save":
                self._submit_form()
            elif event.button.id == "btn-cancel":
                self._hide_form()

    def action_add_host(self) -> None:
        self._show_form(None)

    def action_edit_host(self) -> None:
        host = self.get_selected_host()
        if host:
            self._show_form(host)

    def action_delete_host(self) -> None:
        if self.form_visible:
            return
        host = self.get_selected_host()
        if host:
            self.push_screen(ConfirmScreen(f"Delete host '{host.name}'?"), self._on_delete_confirm)  # type: ignore[arg-type]

    def _on_delete_confirm(self, confirmed: bool) -> None:
        if confirmed:
            host = self.get_selected_host()
            if host:
                backup_config(self.parser.config_path)
                self.parser.remove_host(host.name)
                self.tracker.mark_modified(host.name)
                self.load_hosts()
                self.refresh_list()
                self.show_status(f"Deleted host: {host.name}")

    def action_yank_host(self) -> None:
        if self.form_visible:
            return
        host = self.get_selected_host()
        if host:
            config_str = host.to_config_string()
            if copy_to_clipboard(config_str):
                self.tracker.mark_used(host.name)
                self.show_status(f"Yanked config for: {host.name}")
            else:
                self.show_status("Failed to copy to clipboard", is_error=True)

    def action_copy_ssh_command(self) -> None:
        if self.form_visible:
            return
        host = self.get_selected_host()
        if host:
            if not host.hostname:
                self.show_status("No hostname configured", is_error=True)
                return
            ssh_cmd = host.to_ssh_command()
            if copy_to_clipboard(ssh_cmd):
                self.tracker.mark_used(host.name)
                self.show_status(f"Copied SSH command for: {host.name}")
            else:
                self.show_status("Failed to copy to clipboard", is_error=True)

    def action_copy_ssh_with_password(self) -> None:
        if self.form_visible:
            return
        host = self.get_selected_host()
        if host:
            if not host.hostname:
                self.show_status("No hostname configured", is_error=True)
                return
            if not self.vault.can_store_password():
                self.show_status("Vault unavailable", is_error=True)
                return
            try:
                password = self.vault.get_password(host.name)
            except ValueError:
                password = None
            if not password:
                self.show_status("No password stored for this host", is_error=True)
                return
            ssh_cmd = host.to_ssh_command()
            sshpass_cmd = f"sshpass -p '{password}' {ssh_cmd}"
            if copy_to_clipboard(sshpass_cmd):
                self.tracker.mark_used(host.name)
                self.show_status(f"Copied sshpass command for: {host.name}")
            else:
                self.show_status("Failed to copy to clipboard", is_error=True)

    def action_test_connection(self) -> None:
        if self.form_visible:
            return
        host = self.get_selected_host()
        if not host:
            return
        if not host.hostname:
            self.show_status("No hostname configured", is_error=True)
            return

        self.show_status(f"Testing connection to {host.get_effective_hostname()}...")
        success, message = test_connection(
            host.get_effective_hostname(), host.port or 22
        )
        self.tracker.mark_used(host.name)
        if success:
            self.show_status(f"✓ {host.name}: {message}")
        else:
            self.show_status(f"✗ {host.name}: {message}", is_error=True)

    def action_show_detail(self) -> None:
        if self.form_visible:
            return
        self._update_detail_panel()

    def action_cancel_or_close_form(self) -> None:
        if self.form_visible:
            self._hide_form()
        else:
            self.current_view = "list"
            list_view = self.query_one("#host-list", ListView)
            list_view.focus()

    def action_activate_focused_button(self) -> None:
        focused = self.focused
        if not isinstance(focused, Button):
            return
        
        if self.form_visible:
            if focused.id == "btn-save":
                self._submit_form()
                return
            elif focused.id == "btn-cancel":
                self._hide_form()
                return
        
        current_screen = self.screen
        if isinstance(current_screen, HelpScreen):
            if focused.id == "btn-close":
                self.pop_screen()
        elif isinstance(current_screen, ConfirmScreen):
            if focused.id == "btn-yes":
                self.pop_screen()
                self._on_delete_confirm(True)
            elif focused.id == "btn-no":
                self.pop_screen()
                self._on_delete_confirm(False)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_quit(self) -> None:
        self.exit()


class ConfirmScreen(Screen):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Static(self.message)
        with Horizontal():
            yield Button("Yes", id="btn-yes", variant="primary")
            yield Button("No", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if event.button.id == "btn-yes":
            self.app._on_delete_confirm(True)  # type: ignore[attr-defined]
        else:
            self.app._on_delete_confirm(False)  # type: ignore[attr-defined]


class HelpScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Keyboard Shortcuts", id="help-title")
        yield Static("[b]Navigation[/b]")
        yield Static("  j / k     - Move up/down")
        yield Static("  g / G     - Go to top/bottom")
        yield Static("  /         - Search/filter hosts")
        yield Static("")
        yield Static("[b]Host Actions[/b]")
        yield Static("  a         - Add new host")
        yield Static("  e         - Edit selected host")
        yield Static("  d         - Delete selected host")
        yield Static("  y         - Yank/copy host config")
        yield Static("  c         - Copy SSH command")
        yield Static("  P         - Copy SSH command with password (sshpass)")
        yield Static("  t         - Test connection")
        yield Static("  Enter     - Show host details")
        yield Static("")
        yield Static("[b]Sorting[/b]")
        yield Static("  n         - Sort by name")
        yield Static("  m         - Sort by last modified")
        yield Static("  u         - Sort by last used")
        yield Static("")
        yield Static("[b]Other[/b]")
        yield Static("  Esc       - Cancel / Close form")
        yield Static("  ?         - Show this help")
        yield Static("  q         - Quit")
        yield Static("")
        yield Button("Close", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


def main():
    app = SSHConfigApp()
    app.run()


if __name__ == "__main__":
    main()
