import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class HostUsage:
    last_used: float = 0.0
    last_modified: float = 0.0


class UsageTracker:
    TRACKER_PATH = Path.home() / ".ssh" / "ssh_config_manager.json"

    def __init__(self):
        self._data: dict[str, HostUsage] = {}
        self._load()

    def _load(self) -> None:
        if self.TRACKER_PATH.exists():
            try:
                data = json.loads(self.TRACKER_PATH.read_text())
                self._data = {k: HostUsage(**v) for k, v in data.items()}
            except (json.JSONDecodeError, TypeError):
                self._data = {}

    def _save(self) -> None:
        data = {k: {"last_used": v.last_used, "last_modified": v.last_modified} for k, v in self._data.items()}
        self.TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.TRACKER_PATH.write_text(json.dumps(data, indent=2))

    def mark_used(self, host_name: str) -> None:
        import time
        if host_name not in self._data:
            self._data[host_name] = HostUsage()
        self._data[host_name].last_used = time.time()
        self._save()

    def mark_modified(self, host_name: str) -> None:
        import time
        if host_name not in self._data:
            self._data[host_name] = HostUsage()
        self._data[host_name].last_modified = time.time()
        self._save()

    def get_usage(self, host_name: str) -> Optional[HostUsage]:
        return self._data.get(host_name)

    def get_all_usage(self) -> dict[str, HostUsage]:
        return self._data.copy()


def test_connection(hostname: str, port: int = 22, timeout: int = 5) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), hostname],
            capture_output=True,
            text=True,
            timeout=timeout + 1,
        )
        if result.returncode == 0:
            return True, "Host is reachable"
        return False, "Host is not reachable"
    except subprocess.TimeoutExpired:
        return False, "Connection timed out"
    except FileNotFoundError:
        return False, "ping command not found"
    except Exception as e:
        return False, str(e)


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(
            ["pbcopy"],
            input=text,
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except Exception:
        return False


def backup_config(config_path: Path) -> Optional[Path]:
    import shutil
    import time

    if not config_path.exists():
        return None

    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"config_{timestamp}"
    shutil.copy2(config_path, backup_path)
    return backup_path


def validate_hostname(hostname: str) -> bool:
    import re

    pattern = r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
    return bool(re.match(pattern, hostname)) or hostname.replace(".", "").replace("-", "").isalnum()
