# Product Design Review: Remote Server Monitor (RSM)
## Terminal-Based SSH Monitoring Tool

**Version:** 1.0  
**Date:** January 2025  
**Project Codename:** RSM (Remote Server Monitor)  
**Target Developer:** Junior Developer Implementation

---

## Executive Summary

This Product Design Review outlines the development of a terminal-based remote server monitoring tool similar to btop but designed for monitoring multiple remote servers via SSH. The tool will use Python with the Textual framework, employ an agent-less architecture requiring no remote installation, and be released under a source-available license that permits modification but restricts commercial use.

### Key Features
- **Agent-less monitoring** via SSH command execution
- **Terminal UI** with real-time updates using Textual
- **Multi-server support** with tabbed/split views
- **Service monitoring** for Apache, Nginx, Node.js, databases
- **Log tailing** with regex filtering
- **Modular plugin architecture**
- **Data export** (JSON, Prometheus, CSV)
- **Cross-platform** (Linux, FreeBSD, OpenBSD, macOS)

---

## License Recommendation

Based on your requirement to allow modifications but prevent commercial use, I recommend one of these approaches:

### Option 1: Commons Clause + Apache 2.0 (Recommended)
```
Licensed under the Apache License, Version 2.0 with Commons Clause
Commercial use restriction: Without a commercial license, this software 
and derivatives may not be sold or incorporated into commercial products.
```

### Option 2: Creative Commons BY-NC-SA 4.0
- Allows: Sharing, adaptation, non-commercial use
- Requires: Attribution, share-alike, non-commercial only
- Note: Not traditionally used for software but legally valid

### Option 3: Custom Dual License
- Free tier: Non-commercial use only with source disclosure
- Paid tier: Commercial license available for enterprises

**Recommendation:** Use Commons Clause + Apache 2.0 as it's becoming standard for source-available projects that restrict commercial use while maintaining clear terms.

---

## Technical Architecture

### Core Technology Stack
```yaml
Language: Python 3.9+
UI Framework: Textual 0.40+
SSH Library: Paramiko 3.x
Configuration: TOML (tomli/tomli_w)
Async Framework: asyncio
Testing: pytest + pytest-asyncio
Packaging: setuptools/poetry
```

### Agent-less Architecture Overview

The tool connects to remote servers via SSH and executes standard Unix commands to gather metrics, requiring zero installation on target servers:

```python
# Example architecture
class RemoteServer:
    """Represents a single SSH connection to a remote server"""
    
    def __init__(self, hostname, username, port=22):
        self.ssh_client = paramiko.SSHClient()
        self.hostname = hostname
        self.metrics_cache = {}
        
    async def execute_command(self, command):
        """Execute command via SSH and return output"""
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        return stdout.read().decode('utf-8')
        
    async def get_cpu_usage(self):
        """Get CPU usage by parsing /proc/stat or top output"""
        # Linux: cat /proc/stat
        # BSD/macOS: top -l 1 -n 0
        pass
```

### SSH Connection Management

```yaml
Connection Strategy:
  - Use native SSH config (~/.ssh/config)
  - Support SSH keys (no password storage)
  - Connection pooling per server
  - Automatic reconnection with exponential backoff
  - ControlMaster multiplexing when available
  
Performance Optimizations:
  - Batch command execution
  - Configurable polling intervals
  - Command output caching
  - Compression for slow links
```

---

## Detailed Implementation Plan

### Phase 1: Core Foundation (Weeks 1-3)

#### 1.1 Project Setup
```bash
remote-server-monitor/
├── rsm/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── core/
│   │   ├── ssh_manager.py   # SSH connection handling
│   │   ├── metrics.py       # Metric collection base
│   │   └── config.py        # Configuration management
│   ├── collectors/
│   │   ├── base.py         # Base collector class
│   │   ├── system.py       # CPU, memory, disk
│   │   └── network.py      # Network statistics
│   ├── ui/
│   │   ├── app.py          # Main Textual app
│   │   ├── widgets/        # Custom widgets
│   │   └── screens/        # Screen definitions
│   └── utils/
│       ├── platform.py     # Platform detection
│       └── parsers.py      # Output parsers
├── plugins/                # Plugin directory
├── tests/
├── docs/
├── config.toml.example
└── pyproject.toml
```

#### 1.2 SSH Connection Manager
```python
# rsm/core/ssh_manager.py
import asyncio
import asyncssh
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class SSHConfig:
    hostname: str
    username: str
    port: int = 22
    key_filename: Optional[str] = None
    
class SSHConnectionPool:
    """Manages SSH connections with pooling and reconnection"""
    
    def __init__(self, max_connections: int = 5):
        self.connections: Dict[str, asyncssh.SSHClient] = {}
        self.configs: Dict[str, SSHConfig] = {}
        self.max_connections = max_connections
        
    async def add_server(self, name: str, config: SSHConfig):
        """Add a server to the pool"""
        self.configs[name] = config
        await self._connect(name)
        
    async def execute(self, server: str, command: str) -> str:
        """Execute command on specified server"""
        if server not in self.connections:
            await self._connect(server)
            
        try:
            result = await self.connections[server].run(command)
            return result.stdout
        except Exception as e:
            # Handle reconnection
            await self._reconnect(server)
            raise
```

#### 1.3 Platform Abstraction Layer
```python
# rsm/utils/platform.py
import platform
from enum import Enum
from abc import ABC, abstractmethod

class Platform(Enum):
    LINUX = "linux"
    FREEBSD = "freebsd"
    OPENBSD = "openbsd"
    MACOS = "darwin"
    
class PlatformCommands(ABC):
    """Abstract base for platform-specific commands"""
    
    @abstractmethod
    def cpu_usage_cmd(self) -> str:
        pass
        
    @abstractmethod
    def memory_info_cmd(self) -> str:
        pass
        
class LinuxCommands(PlatformCommands):
    def cpu_usage_cmd(self) -> str:
        return "cat /proc/stat"
        
    def memory_info_cmd(self) -> str:
        return "cat /proc/meminfo"
        
class BSDCommands(PlatformCommands):
    def cpu_usage_cmd(self) -> str:
        return "top -l 1 -n 0"
        
    def memory_info_cmd(self) -> str:
        return "sysctl -n hw.physmem hw.usermem"
```

### Phase 2: Metrics Collection (Weeks 4-5)

#### 2.1 Base Collector Architecture
```python
# rsm/collectors/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio

class MetricCollector(ABC):
    """Base class for all metric collectors"""
    
    def __init__(self, ssh_pool: SSHConnectionPool):
        self.ssh_pool = ssh_pool
        self.cache_duration = 2.0  # seconds
        self._cache: Dict[str, Any] = {}
        self._last_update: Dict[str, float] = {}
        
    @abstractmethod
    async def collect(self, server: str) -> Dict[str, Any]:
        """Collect metrics from a server"""
        pass
        
    @abstractmethod
    def parse_output(self, output: str, platform: Platform) -> Dict[str, Any]:
        """Parse command output into metrics"""
        pass
        
    async def get_metrics(self, server: str) -> Dict[str, Any]:
        """Get metrics with caching"""
        now = asyncio.get_event_loop().time()
        
        if (server in self._cache and 
            now - self._last_update.get(server, 0) < self.cache_duration):
            return self._cache[server]
            
        metrics = await self.collect(server)
        self._cache[server] = metrics
        self._last_update[server] = now
        return metrics
```

#### 2.2 System Metrics Collector
```python
# rsm/collectors/system.py
import re
from typing import Dict, Any

class SystemMetricsCollector(MetricCollector):
    """Collects CPU, memory, disk, and load metrics"""
    
    async def collect(self, server: str) -> Dict[str, Any]:
        platform = await self.detect_platform(server)
        commands = self.get_platform_commands(platform)
        
        # Execute commands in parallel
        results = await asyncio.gather(
            self.ssh_pool.execute(server, commands.cpu_usage_cmd()),
            self.ssh_pool.execute(server, commands.memory_info_cmd()),
            self.ssh_pool.execute(server, "df -h"),
            self.ssh_pool.execute(server, "uptime"),
        )
        
        return {
            'cpu': self.parse_cpu(results[0], platform),
            'memory': self.parse_memory(results[1], platform),
            'disk': self.parse_disk(results[2]),
            'load': self.parse_load(results[3]),
        }
        
    def parse_cpu(self, output: str, platform: Platform) -> Dict[str, float]:
        """Parse CPU usage from platform-specific output"""
        if platform == Platform.LINUX:
            # Parse /proc/stat
            lines = output.strip().split('\n')
            cpu_line = lines[0].split()
            
            user = int(cpu_line[1])
            nice = int(cpu_line[2])
            system = int(cpu_line[3])
            idle = int(cpu_line[4])
            
            total = user + nice + system + idle
            usage = 100.0 * (total - idle) / total if total > 0 else 0
            
            return {'usage_percent': usage}
```

### Phase 3: Terminal UI Implementation (Weeks 6-7)

#### 3.1 Main Application Structure
```python
# rsm/ui/app.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual.containers import Container
from typing import List

class RemoteServerMonitor(App):
    """Main TUI application"""
    
    CSS = """
    .metrics-grid {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        margin: 1;
    }
    
    .metric-panel {
        border: solid green;
        height: 100%;
    }
    """
    
    def __init__(self, config_file: str):
        super().__init__()
        self.config = self.load_config(config_file)
        self.ssh_pool = SSHConnectionPool()
        self.collectors = self.init_collectors()
        
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with TabbedContent():
            for server in self.config['servers']:
                with TabPane(server['name'], id=f"server-{server['name']}"):
                    yield ServerDashboard(server['name'], self.collectors)
                    
        yield Footer()
        
    async def on_mount(self) -> None:
        """Initialize SSH connections when app starts"""
        for server in self.config['servers']:
            await self.ssh_pool.add_server(
                server['name'],
                SSHConfig(
                    hostname=server['hostname'],
                    username=server['username'],
                    port=server.get('port', 22)
                )
            )
        
        # Start metric collection
        self.set_interval(2.0, self.update_metrics)
```

#### 3.2 Custom Widgets
```python
# rsm/ui/widgets/cpu_widget.py
from textual.widget import Widget
from textual.reactive import reactive
from rich.console import RenderableType
from rich.panel import Panel
from rich.progress import Progress, BarColumn

class CPUWidget(Widget):
    """Widget displaying CPU usage"""
    
    cpu_usage = reactive(0.0)
    
    def render(self) -> RenderableType:
        progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        
        task = progress.add_task("CPU", total=100)
        progress.update(task, completed=self.cpu_usage)
        
        return Panel(
            progress,
            title="CPU Usage",
            border_style="green" if self.cpu_usage < 80 else "red"
        )
```

### Phase 4: Service Monitoring (Weeks 8-9)

#### 4.1 Web Server Monitoring
```python
# rsm/collectors/webserver.py
class WebServerCollector(MetricCollector):
    """Collects metrics for Apache and Nginx"""
    
    NGINX_STATUS_PATTERN = re.compile(
        r'Active connections:\s*(\d+).*'
        r'(\d+)\s+(\d+)\s+(\d+).*'
        r'Reading:\s*(\d+).*Writing:\s*(\d+).*Waiting:\s*(\d+)',
        re.DOTALL
    )
    
    async def collect(self, server: str) -> Dict[str, Any]:
        # Check which web servers are running
        nginx_check = await self.ssh_pool.execute(server, "pgrep nginx")
        apache_check = await self.ssh_pool.execute(server, "pgrep apache2")
        
        metrics = {}
        
        if nginx_check:
            # Get nginx status
            status = await self.ssh_pool.execute(
                server, 
                "curl -s http://localhost/nginx_status"
            )
            metrics['nginx'] = self.parse_nginx_status(status)
            
        if apache_check:
            # Get apache status
            status = await self.ssh_pool.execute(
                server,
                "curl -s http://localhost/server-status?auto"
            )
            metrics['apache'] = self.parse_apache_status(status)
            
        return metrics
```

#### 4.2 Node.js Application Monitoring
```python
# rsm/collectors/nodejs.py
class NodeJSCollector(MetricCollector):
    """Collects metrics for Node.js applications"""
    
    async def collect(self, server: str) -> Dict[str, Any]:
        # Find Node.js processes
        ps_output = await self.ssh_pool.execute(
            server,
            "ps aux | grep node | grep -v grep"
        )
        
        processes = self.parse_processes(ps_output)
        metrics = {'processes': []}
        
        for proc in processes:
            # Get process details
            proc_info = {
                'pid': proc['pid'],
                'name': proc['name'],
                'cpu': proc['cpu'],
                'memory': proc['memory'],
            }
            
            # Try to get PM2 info if available
            pm2_info = await self.get_pm2_info(server, proc['name'])
            if pm2_info:
                proc_info.update(pm2_info)
                
            metrics['processes'].append(proc_info)
            
        return metrics
```

### Phase 5: Log Monitoring (Week 10)

#### 5.1 Log Tailer Implementation
```python
# rsm/collectors/logs.py
import asyncio
from typing import AsyncIterator, Pattern
import re

class LogTailer:
    """Asynchronous log tailer with filtering"""
    
    def __init__(self, ssh_pool: SSHConnectionPool):
        self.ssh_pool = ssh_pool
        self.active_tails = {}
        
    async def tail_log(
        self, 
        server: str, 
        file_path: str,
        filter_pattern: Optional[Pattern] = None
    ) -> AsyncIterator[str]:
        """Tail a log file with optional filtering"""
        
        # Start tail process
        connection = await self.ssh_pool.get_connection(server)
        process = await connection.create_process(
            f'tail -F {file_path}',
            stdout=asyncio.subprocess.PIPE
        )
        
        self.active_tails[f"{server}:{file_path}"] = process
        
        try:
            async for line in process.stdout:
                line = line.decode('utf-8').strip()
                
                if filter_pattern and not filter_pattern.search(line):
                    continue
                    
                yield line
        finally:
            process.terminate()
            del self.active_tails[f"{server}:{file_path}"]
```

### Phase 6: Plugin Architecture (Week 11)

#### 6.1 Plugin System Design
```python
# rsm/plugins/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import importlib.util
import os

class Plugin(ABC):
    """Base class for all plugins"""
    
    name: str = "unnamed"
    version: str = "1.0.0"
    author: str = "unknown"
    
    @abstractmethod
    async def collect(self, ssh_pool: SSHConnectionPool, server: str) -> Dict[str, Any]:
        """Collect metrics from server"""
        pass
        
    @abstractmethod
    def get_widget(self) -> Widget:
        """Return Textual widget for displaying metrics"""
        pass
        
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        return True

class PluginManager:
    """Manages loading and execution of plugins"""
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Plugin] = {}
        
    def load_plugins(self) -> None:
        """Load all plugins from plugin directory"""
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                self._load_plugin(filename)
                
    def _load_plugin(self, filename: str) -> None:
        """Load a single plugin file"""
        filepath = os.path.join(self.plugin_dir, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find Plugin subclasses
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Plugin) and 
                attr is not Plugin):
                plugin = attr()
                self.plugins[plugin.name] = plugin
```

#### 6.2 Example Plugin
```python
# plugins/mysql_monitor.py
from rsm.plugins.base import Plugin
from textual.widgets import Static
from rich.table import Table

class MySQLMonitor(Plugin):
    """Monitor MySQL database metrics"""
    
    name = "mysql_monitor"
    version = "1.0.0"
    author = "RSM Team"
    
    async def collect(self, ssh_pool, server):
        # Check if MySQL is running
        check = await ssh_pool.execute(server, "pgrep mysqld")
        if not check:
            return {'status': 'not_running'}
            
        # Get MySQL statistics
        stats = await ssh_pool.execute(
            server,
            "mysql -e 'SHOW GLOBAL STATUS' | grep -E 'Connections|Queries|Threads'"
        )
        
        return self.parse_mysql_stats(stats)
        
    def get_widget(self):
        return MySQLWidget()
```

### Phase 7: Data Export (Week 12)

#### 7.1 Export Formats Implementation
```python
# rsm/exporters/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import csv
from datetime import datetime

class Exporter(ABC):
    """Base class for metric exporters"""
    
    @abstractmethod
    def export(self, metrics: Dict[str, Any], output_file: str) -> None:
        pass

class PrometheusExporter(Exporter):
    """Export metrics in Prometheus format"""
    
    def export(self, metrics: Dict[str, Any], output_file: str) -> None:
        timestamp = int(datetime.now().timestamp() * 1000)
        
        with open(output_file, 'w') as f:
            for server, server_metrics in metrics.items():
                # System metrics
                if 'cpu' in server_metrics:
                    f.write(f'node_cpu_usage{{server="{server}"}} {server_metrics["cpu"]["usage_percent"]} {timestamp}\n')
                
                if 'memory' in server_metrics:
                    mem = server_metrics['memory']
                    f.write(f'node_memory_used_bytes{{server="{server}"}} {mem["used_bytes"]} {timestamp}\n')
                    f.write(f'node_memory_total_bytes{{server="{server}"}} {mem["total_bytes"]} {timestamp}\n')
```

---

## Configuration Specification

### config.toml Format
```toml
[general]
poll_interval = 2.0
enable_compression = true
connection_timeout = 30
retry_attempts = 3

[[servers]]
name = "web-server-1"
hostname = "192.168.1.10"
username = "monitor"
port = 22
# SSH key path is read from ~/.ssh/config or ~/.ssh/id_rsa

[[servers]]
name = "db-server-1"
hostname = "db.example.com"
username = "monitor"

[collectors]
system = { enabled = true, interval = 2.0 }
network = { enabled = true, interval = 5.0 }
webserver = { enabled = true, interval = 10.0 }
nodejs = { enabled = true, interval = 10.0 }

[plugins]
enabled = ["mysql_monitor", "redis_monitor"]
directory = "./plugins"

[export]
prometheus = { enabled = true, port = 9100 }
json = { enabled = false, file = "/tmp/metrics.json" }
```

---

## Performance Considerations

### Resource Usage Targets
- **Memory:** < 50MB per monitored server
- **CPU:** < 5% on monitoring host
- **Network:** < 10KB/s per server average

### Optimization Strategies

1. **Command Batching**
   ```python
   # Execute multiple commands in one SSH session
   commands = "; ".join([
       "cat /proc/stat",
       "cat /proc/meminfo",
       "df -h",
       "uptime"
   ])
   output = await ssh_pool.execute(server, commands)
   ```

2. **Intelligent Caching**
   - Static data (hostname, OS): Cache indefinitely
   - Semi-static (disk space): Cache 60 seconds
   - Dynamic (CPU, memory): Cache 2 seconds
   - Real-time (logs): No caching

3. **Connection Pooling**
   - Maintain 1-3 persistent SSH connections per server
   - Use ControlMaster when available
   - Implement exponential backoff for reconnections

---

## Security Guidelines

### SSH Security
1. **Authentication**
   - Use SSH keys only (no password storage)
   - Support Ed25519 and RSA keys
   - Read from standard SSH locations

2. **Connection Security**
   - Honor ~/.ssh/config settings
   - Support jump hosts/bastion servers
   - Implement rate limiting

3. **Monitoring Account**
   ```bash
   # Create restricted monitoring user on remote servers
   sudo useradd -r -s /bin/bash -d /var/lib/rsm-monitor rsm-monitor
   sudo mkdir -p /var/lib/rsm-monitor/.ssh
   sudo cp ~/.ssh/authorized_keys /var/lib/rsm-monitor/.ssh/
   sudo chown -R rsm-monitor: /var/lib/rsm-monitor
   
   # Grant minimal required permissions
   sudo usermod -a -G systemd-journal rsm-monitor  # For log access
   ```

---

## Testing Strategy

### Unit Tests
```python
# tests/test_collectors.py
import pytest
from rsm.collectors.system import SystemMetricsCollector
from rsm.utils.platform import Platform

class TestSystemMetricsCollector:
    @pytest.fixture
    def collector(self):
        return SystemMetricsCollector(mock_ssh_pool())
        
    def test_parse_linux_cpu(self, collector):
        output = "cpu  1234 0 5678 9012 0 0 0 0 0 0"
        result = collector.parse_cpu(output, Platform.LINUX)
        assert 'usage_percent' in result
        assert 0 <= result['usage_percent'] <= 100
```

### Integration Tests
- Test against Docker containers running different OS
- Mock SSH connections for CI/CD
- Performance benchmarks for large-scale monitoring

---

## Deployment Guide

### Installation
```bash
# From PyPI (future)
pip install remote-server-monitor

# From source
git clone https://github.com/yourorg/remote-server-monitor
cd remote-server-monitor
pip install -e .
```

### Quick Start
```bash
# Create configuration
cp config.toml.example config.toml
# Edit config.toml with your servers

# Run the monitor
rsm --config config.toml

# Or use command line
rsm --add-server web1:user@192.168.1.10 --add-server db1:user@db.example.com
```

---

## Development Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Core Foundation | 3 weeks | SSH manager, config system, basic UI |
| Phase 2: Metrics Collection | 2 weeks | System metrics, platform abstraction |
| Phase 3: Terminal UI | 2 weeks | Textual implementation, widgets |
| Phase 4: Service Monitoring | 2 weeks | Web servers, Node.js, databases |
| Phase 5: Log Monitoring | 1 week | Log tailing with filters |
| Phase 6: Plugin System | 1 week | Plugin architecture, examples |
| Phase 7: Data Export | 1 week | Prometheus, JSON, CSV export |
| Phase 8: Polish & Docs | 2 weeks | Testing, documentation, packaging |

**Total: 14 weeks (3.5 months)**

---

## Success Metrics

1. **Performance**
   - Monitor 50+ servers simultaneously
   - < 2 second UI update latency
   - < 50MB memory per server

2. **Reliability**
   - 99.9% uptime for monitoring service
   - Automatic reconnection within 30 seconds
   - Graceful degradation on failures

3. **Adoption**
   - 100+ GitHub stars within 6 months
   - Active community contributions
   - Production use in 10+ organizations

---

## Appendix A: Command Reference

### Linux Commands
```bash
# CPU: /proc/stat
# Memory: /proc/meminfo
# Disk: df -h
# Network: /proc/net/dev
# Processes: ps aux
```

### BSD/macOS Commands
```bash
# CPU: top -l 1 -n 0
# Memory: sysctl hw.memsize hw.memused
# Disk: df -h
# Network: netstat -ibn
# Processes: ps aux
```

---

## Appendix B: Research Summary

The research phase revealed that agent-less monitoring via SSH is a proven approach used successfully by tools like rtop and SshSysMon. Key findings:

1. **SSH Optimization**: Connection multiplexing can reduce overhead by 40-60%
2. **UI Performance**: Textual provides excellent performance with modern API
3. **Cross-Platform**: Abstract system commands early to avoid refactoring
4. **Plugin Architecture**: External process plugins provide best isolation
5. **Security**: Use existing SSH infrastructure, don't reinvent

This PDR incorporates all research findings adapted specifically for a Python/Textual implementation with agent-less architecture.