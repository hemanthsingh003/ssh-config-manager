import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SSHHost:
    name: str
    hostname: Optional[str] = None
    user: Optional[str] = None
    port: Optional[int] = None
    identity_file: Optional[str] = None
    proxy_jump: Optional[str] = None
    forward_agent: Optional[bool] = None
    server_alive_interval: Optional[int] = None
    strict_host_key_checking: Optional[str] = None
    user_known_hosts_file: Optional[str] = None
    password: Optional[str] = None
    options: dict = field(default_factory=dict)
    line_number: int = 0

    def to_config_string(self) -> str:
        lines = [f"Host {self.name}"]
        if self.hostname:
            lines.append(f"    HostName {self.hostname}")
        if self.user:
            lines.append(f"    User {self.user}")
        if self.port:
            lines.append(f"    Port {self.port}")
        if self.identity_file:
            lines.append(f"    IdentityFile {self.identity_file}")
        if self.proxy_jump:
            lines.append(f"    ProxyJump {self.proxy_jump}")
        if self.forward_agent is not None:
            lines.append(f"    ForwardAgent {'yes' if self.forward_agent else 'no'}")
        if self.server_alive_interval is not None:
            lines.append(f"    ServerAliveInterval {self.server_alive_interval}")
        if self.strict_host_key_checking is not None:
            lines.append(f"    StrictHostKeyChecking {self.strict_host_key_checking}")
        if self.user_known_hosts_file:
            lines.append(f"    UserKnownHostsFile {self.user_known_hosts_file}")
        for key, value in self.options.items():
            lines.append(f"    {key} {value}")
        return "\n".join(lines)

    def to_ssh_command(self, include_password: bool = False) -> str:
        parts = ["ssh"]
        if self.port:
            parts.extend(["-p", str(self.port)])
        if self.identity_file:
            parts.extend(["-i", self.identity_file])
        if self.proxy_jump:
            parts.extend(["-J", self.proxy_jump])
        if self.forward_agent:
            parts.extend(["-A"])
        if self.user:
            target = f"{self.user}@{self.hostname or self.name}"
        else:
            target = self.hostname or self.name
        parts.append(target)
        return " ".join(parts)

    def get_effective_hostname(self) -> str:
        return self.hostname or self.name


class SSHConfigParser:
    SSH_CONFIG_PATH = Path.home() / ".ssh" / "config"

    COMMON_OPTIONS = {
        "hostname": "hostname",
        "host": "name",
        "user": "user",
        "port": "port",
        "identityfile": "identity_file",
        "proxyjump": "proxy_jump",
        "forwardagent": "forward_agent",
        "serveraliveinterval": "server_alive_interval",
        "stricthostkeychecking": "strict_host_key_checking",
        "userknownhostsfile": "user_known_hosts_file",
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.SSH_CONFIG_PATH

    def parse(self) -> list[SSHHost]:
        if not self.config_path.exists():
            return []

        hosts = []
        current_host: Optional[SSHHost] = None

        with open(self.config_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.rstrip("\n")
                stripped = line.strip()

                if not stripped or stripped.startswith("#"):
                    continue

                if stripped.lower().startswith("host "):
                    if current_host:
                        hosts.append(current_host)

                    host_name = stripped[5:].strip()
                    if host_name and not host_name.startswith("*"):
                        current_host = SSHHost(name=host_name, line_number=line_num)
                    else:
                        current_host = None
                elif current_host:
                    key, value = self._parse_option(stripped)
                    if key:
                        self._set_option(current_host, key, value, line_num)

        if current_host:
            hosts.append(current_host)

        return hosts

    def _parse_option(self, line: str) -> tuple[Optional[str], Optional[str]]:
        match = re.match(r"^(\S+)\s+(.*)$", line)
        if match:
            return match.group(1).lower(), match.group(2).strip()
        return None, None

    def _set_option(self, host: SSHHost, key: str, value: Optional[str], line_num: int):
        if value is None:
            return
        mapped_key = self.COMMON_OPTIONS.get(key)
        if mapped_key:
            if mapped_key == "port":
                try:
                    setattr(host, mapped_key, int(value))
                except ValueError:
                    host.options[key] = value
            elif mapped_key == "forward_agent":
                setattr(host, mapped_key, value.lower() in ("yes", "true", "1"))
            elif mapped_key == "name":
                pass
            else:
                setattr(host, mapped_key, value)
        else:
            host.options[key] = value

    def write(self, hosts: list[SSHHost]) -> None:
        config_dir = self.config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            for host in hosts:
                f.write(host.to_config_string())
                f.write("\n\n")

    def add_host(self, host: SSHHost) -> None:
        hosts = self.parse()
        hosts.append(host)
        self.write(hosts)

    def update_host(self, old_name: str, new_host: SSHHost) -> None:
        hosts = self.parse()
        for i, host in enumerate(hosts):
            if host.name == old_name:
                hosts[i] = new_host
                break
        self.write(hosts)

    def remove_host(self, name: str) -> None:
        hosts = [h for h in self.parse() if h.name != name]
        self.write(hosts)

    def find_duplicate_names(self) -> list[tuple[str, list[int]]]:
        hosts = self.parse()
        name_to_lines: dict[str, list[int]] = {}
        for host in hosts:
            if host.name not in name_to_lines:
                name_to_lines[host.name] = []
            name_to_lines[host.name].append(host.line_number)

        return [(name, lines) for name, lines in name_to_lines.items() if len(lines) > 1]

    def get_host(self, name: str) -> Optional[SSHHost]:
        hosts = self.parse()
        for host in hosts:
            if host.name == name:
                return host
        return None

    def search(self, query: str, hosts: Optional[list[SSHHost]] = None) -> list[SSHHost]:
        if hosts is None:
            hosts = self.parse()

        query_lower = query.lower()
        return [
            h
            for h in hosts
            if query_lower in h.name.lower()
            or (h.hostname and query_lower in h.hostname.lower())
            or (h.user and query_lower in h.user.lower())
        ]
