from ansible.plugins.callback import CallbackBase
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from datetime import datetime
import collections
import time

class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'rich_progress'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.console = Console()
        self.logs = collections.deque(maxlen=10)
        self.active_app = None
        self.active_action = "Initializing..."
        self.live = None
        self.is_finished = False
        # Create a persistent spinner to maintain animation state
        self.spinner = Spinner("dots", style="bright_blue")
        self._last_refresh = time.monotonic()

    def _get_context(self, task_name):
        if '|' in task_name:
            parts = [p.strip() for p in task_name.split('|')]
            if len(parts) >= 4:
                app_part = parts[2]
                action = parts[3]
                if app_part.startswith("Group:") or app_part == "Master":
                    return "GLOBAL", app_part, action
                stripped_app = app_part.replace("Serial:", "").strip()
                return "APP", stripped_app, action
        return "INTERNAL", task_name, task_name

    def _render_panel(self):
        log_lines = []
        for line in self.logs:
            try:
                text = Text.from_markup(line)
            except Exception:
                text = Text(line)
            
            text.overflow = "ellipsis"
            text.no_wrap = True
            log_lines.append(text)
            
        while len(log_lines) < 10:
            log_lines.append(Text(""))
        
        border_color = "grey37"
        title_color = "bright_blue" if not self.is_finished else "bright_green"
        
        if self.is_finished:
            header_icon = "✓" 
            status_text = f"Done: {self.active_action}"
        else:
            header_icon = "•" 
            status_text = f"Running: {self.active_action}"

        body_items = []
        if not self.is_finished:
            # Update spinner style and text
            self.spinner.style = title_color
            self.spinner.text = Text(f" {self.active_action}", style="grey50")
            body_items.append(self.spinner)
            body_items.append(Text(""))
        
        body_items.extend(log_lines)
        
        return Panel(
            Group(*body_items),
            title=Text(f" {header_icon} {self.active_app} ", style=f"bold {title_color}"),
            subtitle=Text(f" {status_text} ", style="grey50"),
            border_style=border_color,
            padding=(0, 1),
            title_align="left"
        )

    def _add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_msg = message.replace("🚀", "-").replace("..", "-").replace("✅", "✓").replace("⠿", "✓").replace("❌", "x").replace("↺", "retry")
        self.logs.append(f"[grey37][{timestamp}][/] {clean_msg}")

    def _stop_live(self, is_finished=True):
        if self.live:
            self.is_finished = is_finished
            self.live.update(self._render_panel())
            self.live.stop()
            self.live = None

    def v2_playbook_on_play_start(self, play):
        name = play.get_name()
        self.console.print(f"\n[grey37]PLAY [{name}][/grey37] {'─' * (max(10, self.console.width - len(name) - 8))}")

    def v2_playbook_on_task_start(self, task, is_conditional):
        raw_name = task.get_name()
        ctx_type, app, action = self._get_context(raw_name)
        
        if ctx_type == "GLOBAL":
            self._stop_live(is_finished=True)
            self.active_app = None
            self.console.print(f"\n[grey50]── {raw_name} ──[/grey50]")
            
        elif ctx_type == "APP":
            if app != self.active_app:
                self._stop_live(is_finished=True)
                self.active_app = app
                self.is_finished = False
                self.logs.clear()
                self.console.print(f"\n[grey70]Deploying: {app}[/grey70]")
                # Live will call _render_panel 10 times a second
                self.live = Live(get_renderable=self._render_panel, console=self.console, refresh_per_second=10, transient=False)
                self.live.start()
            
            self.active_action = action
            self._add_log(f"[grey50]- {action}[/]")

        elif ctx_type == "INTERNAL":
            if self.active_app:
                self.active_action = raw_name
                self._add_log(f"  [grey37]  {raw_name}[/]")
            else:
                self.console.print(f"[grey37]TASK [{raw_name}][/grey37]")

    def v2_runner_on_start(self, host, task):
        pass

    def v2_runner_retry(self, result):
        res = result._result
        stdout = res.get('stdout', '').strip()
        if "--- DOCKER LOGS ---" in stdout:
            parts = stdout.split("--- DOCKER LOGS ---")
            msg = parts[-1].strip()
            logs = parts[0].strip().split('\n')[-2:]
            for l in logs:
                if l.strip(): self._add_log(f"  [grey37]> {l.strip()}[/]")
        else:
            msg = stdout.split('\n')[-1] if stdout else res.get('msg', 'Retrying...')
        attempt = res.get('attempts', '?')
        self._add_log(f"  [grey50]retry({attempt}):[/] {msg}")

    def v2_runner_on_ok(self, result):
        res = result._result
        msg = "CHANGED" if res.get('changed') else "OK"
        color = "yellow" if msg == "CHANGED" else "green"
        stdout = res.get('stdout', '').strip()
        if stdout and self.active_app and len(stdout) < 200:
            self._add_log(f"  [grey37]> {stdout.splitlines()[-1]}[/]")
        self._add_log(f"  ✓ [{color}]{msg}[/]")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._add_log(f"  [bold red]x FAILED[/]")
        self._stop_live(is_finished=False)

    def v2_playbook_on_stats(self, stats):
        self._stop_live(is_finished=True)
        self.console.print(f"\n[grey37]FINISH {'─' * (max(10, self.console.width - 7))}[/grey37]")

    def __del__(self):
        self._stop_live(is_finished=False)
