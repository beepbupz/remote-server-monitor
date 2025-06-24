# Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Prerequisites
- Python 3.9+
- SSH access to servers you want to monitor
- Terminal with UTF-8 support

### 2. Installation

```bash
# Clone or download the project
git clone <repository-url>
cd remote-server-monitor

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

### 3. Configuration

```bash
# Copy the example configuration
cp config.toml.example config.toml

# Edit config.toml with your server details
nano config.toml  # or use your favorite editor
```

Minimal configuration example:
```toml
[general]
poll_interval = 2.0

[[servers]]
name = "my-server"
hostname = "192.168.1.100"  # or domain name
username = "myuser"
port = 22
```

### 4. Run the Monitor

```bash
rsm --config config.toml
```

### 5. Navigation

- **Tab/Shift+Tab**: Switch between servers
- **r**: Refresh metrics
- **q**: Quit application

## 🔧 Troubleshooting

### Cannot connect to server
1. Test SSH connection: `ssh myuser@192.168.1.100`
2. Check SSH key is set up: `ssh-copy-id myuser@192.168.1.100`
3. Verify port is correct (default: 22)

### Import errors
Make sure all dependencies are installed:
```bash
pip install -e .
```

### Permission denied
Ensure your SSH key has correct permissions:
```bash
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

## 📋 Example Configurations

### Multiple Servers
```toml
[[servers]]
name = "web-1"
hostname = "web1.example.com"
username = "monitor"

[[servers]]
name = "web-2"
hostname = "web2.example.com"
username = "monitor"

[[servers]]
name = "database"
hostname = "10.0.0.50"
username = "dbmonitor"
port = 2222  # Custom SSH port
```

### With Custom Settings
```toml
[general]
poll_interval = 5.0      # Update every 5 seconds
log_level = "DEBUG"      # Show debug logs
connection_timeout = 60  # Longer timeout for slow connections

[[servers]]
name = "remote-server"
hostname = "server.faraway.com"
username = "admin"
key_filename = "/home/user/.ssh/special_key"  # Specific SSH key
```

## 🎯 What You'll See

The monitor displays:
- **CPU Usage**: Percentage and progress bar
- **Memory Usage**: Used/Total with percentage
- **Disk Usage**: Mount points with space utilization
- **System Load**: 1, 5, and 15-minute averages

Each metric is color-coded:
- 🟢 Green: Normal
- 🟡 Yellow: Warning
- 🔴 Red: Critical

## 📚 Next Steps

1. Read the full [README.md](README.md) for detailed information
2. Check [TODO.md](TODO.md) for upcoming features
3. See [DEVELOPMENT.md](DEVELOPMENT.md) to contribute
4. Review [config.toml.example](config.toml.example) for all options