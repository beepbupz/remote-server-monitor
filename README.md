# Remote Server Monitor (RSM)

A terminal-based SSH monitoring tool for multiple remote servers without requiring any agent installation.

## Features

- **Agent-less monitoring** via SSH command execution
- **Terminal UI** with real-time updates using Textual
- **Multi-server support** with tabbed interface
- **Cross-platform** support (Linux, FreeBSD, OpenBSD, macOS)
- **System metrics** monitoring (CPU, memory, disk, load)
- **Service monitoring** (Apache, Nginx, MySQL, PostgreSQL, Redis)
- **Process monitoring** (Node.js, Python, Java, Docker applications)
- **Real-time dashboards** with color-coded health indicators
- **Modular architecture** with plugin support
- **Data export** capabilities (Prometheus, JSON)

## Requirements

- Python 3.9+
- SSH access to target servers
- SSH key-based authentication (recommended)

## Installation

### From source

```bash
git clone https://github.com/beepbupz/remote-server-monitor
cd remote-server-monitor
pip install -e .
```

### Development installation

```bash
pip install -e ".[dev]"
```

## Quick Start

1. Copy the example configuration:
```bash
cp config.toml.example config.toml
```

2. Edit `config.toml` with your server details:
```toml
[[servers]]
name = "my-server"
hostname = "192.168.1.100"
username = "myuser"
port = 22
```

3. Run the monitor:
```bash
rsm --config config.toml
```

Or simply:
```bash
rsm  # Uses config.toml in current directory
```

## Configuration

The configuration file uses TOML format. See `config.toml.example` for all available options.

### Key configuration sections:

- **[general]** - Global settings (polling interval, timeouts, logging)
- **[[servers]]** - Server definitions (hostname, username, port, SSH key)
- **[collectors]** - Metric collector settings
- **[plugins]** - Plugin configuration
- **[export]** - Data export settings

## SSH Setup

RSM uses SSH key-based authentication. Ensure your SSH keys are properly configured:

1. Generate SSH key if needed:
```bash
ssh-keygen -t ed25519 -C "rsm-monitor"
```

2. Copy key to remote servers:
```bash
ssh-copy-id user@remote-server
```

3. Test SSH connection:
```bash
ssh user@remote-server
```

## Usage

### Keyboard Shortcuts

- `q` - Quit application
- `r` - Refresh metrics
- `Tab` - Switch between servers
- `?` - Show help

### Command Line Options

```bash
rsm --help
rsm --version
rsm --config /path/to/config.toml
```

## Architecture

RSM follows a modular architecture:

- **SSH Manager** - Handles connection pooling and command execution
- **Platform Abstraction** - Provides OS-specific command mappings
- **Collectors** - Gather metrics from servers
- **UI** - Textual-based terminal interface
- **Plugins** - Extend functionality with custom collectors

## Development

### Running tests
```bash
pytest
```

### Code formatting
```bash
black rsm/
ruff check rsm/
```

### Type checking
```bash
mypy rsm/
```

## Troubleshooting

### Connection Issues
- Verify SSH access: `ssh user@server`
- Check SSH key permissions: `chmod 600 ~/.ssh/id_*`
- Enable debug logging: Set `log_level = "DEBUG"` in config

### Performance
- Increase poll interval for slow connections
- Enable compression: `enable_compression = true`
- Reduce number of collectors

## License

Apache License 2.0 with Commons Clause - See LICENSE file for details.

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Roadmap

- [x] Service monitoring (Apache, Nginx, MySQL, PostgreSQL, Redis) ✅
- [x] Process monitoring (Node.js, Python, Java, Docker) ✅
- [ ] Log tailing with filtering
- [ ] Alert notifications
- [ ] Historical data storage
- [ ] Web dashboard
- [ ] Enhanced container monitoring