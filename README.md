# SSH Config Manager

A Terminal User Interface (TUI) tool for managing SSH configurations with vim-like keybindings. Built with Textual, it provides an intuitive way to view, add, edit, and organize your SSH hosts.

## Overview

SSH Config Manager eliminates the need to manually edit `~/.ssh/config` by providing a visual interface with powerful features:

- **TUI Interface**: Rich terminal UI built with Textual
- **Vim-like Keybindings**: Navigate and operate efficiently with keyboard shortcuts
- **Password Vault**: Securely store SSH passwords with encryption
- **Quick Actions**: Copy SSH commands, test connections, yank configs
- **Sorting & Filtering**: Sort by name, last modified, or last used; search/filter hosts

## Features

### Core Functionality

- **Parse SSH Config**: Reads and parses `~/.ssh/config` automatically
- **Add Hosts**: Create new SSH host configurations with a form
- **Edit Hosts**: Modify existing host configurations
- **Delete Hosts**: Remove hosts with confirmation dialog
- **View Details**: See full configuration details for any host

### Password Management

- **Encrypted Storage**: Passwords stored using Fernet encryption (AES)
- **Auto-unlock**: Vault unlocks automatically using machine-derived key
- **SSH with Password**: Generate `sshpass` commands for password-based auth

### Quick Actions

- **Copy SSH Command**: Copy `ssh user@hostname` to clipboard
- **Copy with Password**: Copy `sshpass -p 'password' ssh ...` command
- **Yank Config**: Copy full host block to clipboard
- **Test Connection**: Ping host to verify connectivity

### Organization

- **Sort by Name**: Alphabetical sorting
- **Sort by Last Modified**: Most recently modified first
- **Sort by Last Used**: Most recently used first
- **Search/Filter**: Filter hosts by name, hostname, or user

## Keybindings

| Key | Action | Description |
|-----|--------|-------------|
| `j` / `k` | Navigate | Move up/down in host list |
| `g` | Go to Top | Jump to first host |
| `G` | Go to Bottom | Jump to last host |
| `/` | Search | Focus search input |
| `n` | Sort by Name | Sort hosts alphabetically |
| `m` | Sort by Modified | Sort by last modified |
| `u` | Sort by Used | Sort by last used |
| `a` | Add Host | Open add host form |
| `e` | Edit Host | Edit selected host |
| `d` | Delete Host | Delete with confirmation |
| `y` | Yank | Copy host config to clipboard |
| `c` | Copy SSH | Copy SSH command |
| `P` | SSH with Password | Copy sshpass command |
| `t` | Test | Test connection to host |
| `Enter` | Details | Show host details |
| `Esc` | Cancel | Cancel/close form |
| `?` | Help | Show keyboard shortcuts |
| `q` | Quit | Exit application |

## Directory Structure

```
ssh-config-manager/
├── pyproject.toml              # Package configuration
├── README.md                   # This file
├── AGENTS.md                   # Developer guidelines
│
├── sshconfig/                  # Main package
│   ├── __init__.py             # Main TUI application
│   ├── config.py               # SSH config parser
│   ├── vault.py                # Password vault (encryption)
│   ├── utils.py                # Utilities (clipboard, backup, etc.)
│   └── __pycache__/            # Python bytecode
│
└── tests/                      # Test suite
    ├── test_config.py
    └── __init__.py
```

## Installation

```bash
pip install ssh-config-manager
```

That's it! The `sshconfig` command will be available globally.

### From Source (Development)

```bash
pip install -e /path/to/ssh-config-manager
```

### Requirements

- Python 3.10+
- Terminal with Unicode support

## Usage

### Launch the Application

```bash
sshconfig
```

### First Run

On first launch:
1. Application reads your existing `~/.ssh/config`
2. Creates a password vault in `~/.ssh/ssh_config_vault`
3. Initializes usage tracking in `~/.ssh/ssh_config_manager.json`

### Main View

The interface has two panels:

```
┌────────────────────────────────────────────────────────────────┐
│                     SSH Config Manager                         │
├─────────────────────────┬──────────────────────────────────────┤
│ Search... (press /)    │  Config Details                       │
│                         │                                       │
│ ▼ production-server     │  Host: production-server              │
│   user@192.168.1.10    │  HostName: 192.168.1.10               │
│                         │  User: admin                         │
│   staging-server        │  Port: 22                             │
│   user@192.168.1.20    │  IdentityFile: ~/.ssh/id_rsa          │
│                         │                                       │
│   dev-machine          │  Password: stored                     │
│   user@localhost       │                                       │
│                         │  SSH Command:                        │
│                         │  ssh -i ~/.ssh/id_rsa                 │
│                         │    admin@192.168.1.10                │
│                         │                                       │
├─────────────────────────┴──────────────────────────────────────┤
│ vim-like: j/k=navigate  /=search  a=add  e=edit  d=delete ... │
└────────────────────────────────────────────────────────────────┘
```

### Adding a Host

1. Press `a` to open the add form
2. Fill in the fields:
   - **Host**: Name (required)
   - **Hostname**: IP or domain
   - **User**: SSH username
   - **Port**: SSH port (default: 22)
   - **Identity**: Path to SSH key
   - **ProxyJump**: Proxy/jump host
   - **Password**: (optional) Stored securely
3. Press `Enter` on Save or click Save button
4. Press `Esc` to cancel

### Editing a Host

1. Navigate to the host with `j`/`k`
2. Press `e` to open edit form
3. Modify fields
4. Save or cancel

### Deleting a Host

1. Navigate to the host
2. Press `d`
3. Confirm deletion in dialog

### Copying SSH Commands

- `c` - Copy: `ssh user@hostname`
- `y` - Yank: Copy full config block
- `P` - Copy with password: `sshpass -p 'password' ssh ...`

### Testing Connections

1. Select a host
2. Press `t`
3. Application pings the hostname
4. Status shows success/failure

## Password Vault

### How It Works

The password vault uses **Fernet symmetric encryption** (AES-128):

1. **Key Derivation**: Machine ID + salt → PBKDF2 → 32-byte key
2. **Encryption**: AES-128-CTR with HMAC verification
3. **Storage**: Encrypted passwords in `~/.ssh/ssh_config_vault`

### Files Created

| File | Location | Purpose |
|------|----------|---------|
| `ssh_config_vault` | `~/.ssh/` | Encrypted password storage |
| `.ssh_config_vault_salt` | `~/.ssh/` | Salt for key derivation |
| `.ssh_config_vault_verify` | `~/.ssh/` | Verification token |
| `ssh_config_manager.json` | `~/.ssh/` | Usage tracking data |

### Security Notes

- Vault auto-unlocks using machine-derived key
- For higher security, use key-based authentication
- Passwords are encrypted but the key is derived from machine ID

## Configuration

### SSH Config Location

By default, reads from `~/.ssh/config`. Override in code:

```python
from sshconfig.config import SSHConfigParser
parser = SSHConfigParser(config_path=Path("/custom/path"))
```

### Custom Vault Location

Override vault paths in `vault.py`:

```python
class PasswordVault:
    VAULT_PATH = Path("/custom/vault/path")
    SALT_PATH = Path("/custom/salt/path")
    VERIFY_PATH = Path("/custom/verify/path")
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=sshconfig --cov-report=term-missing
```

### Code Quality

```bash
# Install linting tools
pip install ruff black mypy

# Run linter
ruff check .

# Format code
black .

# Type checking
mypy sshconfig/
```

### Code Style

- Follow PEP 8
- Use type hints
- 4 spaces for indentation
- Max line length: 100 characters
- Docstrings for public functions

## Troubleshooting

### "Vault unavailable" Error

The password vault failed to initialize. Ensure:
- `~/.ssh/` directory exists and is writable
- No permission issues with vault files

### Changes Not Saving

- Check if `~/.ssh/config` is writable
- Verify backup was created in `~/.ssh/backups/`

### Connection Test Fails

- Ensure hostname is correct
- Check network connectivity
- Verify SSH port is accessible

### TUI Rendering Issues

- Ensure terminal supports Unicode
- Try increasing terminal size
- Check $TERM variable

## Alternatives

If you need different features, consider:

- **sshm**: SSH config manager with similar features
- **ssh-config**: Node.js SSH config tool
- **o ssh**: Rust-based SSH config manager
- **awless**: Cloud SSH management

## License

MIT License
