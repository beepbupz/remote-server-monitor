# Development Guide

This guide provides detailed information for developers working on the Remote Server Monitor project.

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- SSH access to test servers
- Terminal with UTF-8 support

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourorg/remote-server-monitor
   cd remote-server-monitor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up pre-commit hooks** (when implemented)
   ```bash
   pre-commit install
   ```

## Project Structure

```
remote-server-monitor/
├── rsm/                    # Main package
│   ├── __init__.py        # Package metadata
│   ├── __main__.py        # Entry point
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration management
│   │   └── ssh_manager.py # SSH connection handling
│   ├── collectors/        # Metric collectors
│   │   ├── base.py       # Base collector classes
│   │   └── system.py     # System metrics
│   ├── ui/               # Terminal UI
│   │   ├── app.py       # Main application
│   │   ├── widgets/     # Custom widgets
│   │   └── screens/     # Screen definitions
│   └── utils/            # Utilities
│       └── platform.py   # Platform detection
├── plugins/              # Plugin directory
├── tests/               # Test suite
├── docs/                # Documentation
├── config.toml.example  # Example configuration
├── pyproject.toml       # Project configuration
└── README.md           # Project overview
```

## Architecture Overview

### Core Components

1. **SSH Manager**
   - Handles all SSH connections
   - Implements connection pooling
   - Provides automatic reconnection
   - Manages concurrent command execution

2. **Platform Abstraction**
   - Detects target OS (Linux, BSD, macOS)
   - Provides platform-specific commands
   - Handles command output parsing

3. **Collectors**
   - Modular design for different metric types
   - Base class provides caching and scheduling
   - Each collector handles specific metrics

4. **UI Layer**
   - Built on Textual framework
   - Widget-based architecture
   - Real-time updates via async loops

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Config    │────▶│  SSH Manager │────▶│  Platform  │
└─────────────┘     └──────────────┘     └────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌────────────┐
                    │  Collectors  │◀────│  Commands  │
                    └──────────────┘     └────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   UI Layer   │
                    └──────────────┘
```

## Adding New Features

### Creating a New Collector

1. **Create collector file** in `rsm/collectors/`
   ```python
   from ..collectors.base import MetricCollector
   from ..utils.platform import Platform
   
   class MyCollector(MetricCollector):
       name = "my_metrics"
       description = "Description of metrics"
       default_interval = 5.0
       
       async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
           # Implementation
           pass
   ```

2. **Register in the application**
   ```python
   # In rsm/ui/app.py
   from ..collectors.my_collector import MyCollector
   
   my_collector = MyCollector(self.ssh_pool)
   self.collector_registry.register(my_collector)
   ```

3. **Add configuration option**
   ```toml
   # In config.toml
   [collectors]
   my_metrics = { enabled = true, interval = 5.0 }
   ```

### Creating a New Widget

1. **Create widget class**
   ```python
   from textual.widget import Widget
   from rich.panel import Panel
   
   class MyWidget(MetricWidget):
       def render(self) -> Panel:
           # Render logic
           pass
   ```

2. **Add to dashboard**
   ```python
   # In ServerDashboard.compose()
   yield MyWidget()
   ```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rsm --cov-report=html

# Run specific test file
pytest tests/test_ssh_manager.py

# Run with verbose output
pytest -v
```

### Writing Tests

Example test structure:
```python
import pytest
from rsm.core.ssh_manager import SSHConnectionPool

@pytest.mark.asyncio
async def test_connection_pool():
    pool = SSHConnectionPool()
    # Test implementation
```

## Code Style

### Formatting
```bash
# Format code with Black
black rsm/

# Check without modifying
black --check rsm/
```

### Linting
```bash
# Run Ruff linter
ruff check rsm/

# Fix auto-fixable issues
ruff check --fix rsm/
```

### Type Checking
```bash
# Run mypy
mypy rsm/
```

## Debugging

### Enable Debug Logging
Set in `config.toml`:
```toml
[general]
log_level = "DEBUG"
```

### Common Issues

1. **SSH Connection Failures**
   - Check SSH key permissions: `chmod 600 ~/.ssh/id_*`
   - Verify server connectivity: `ssh user@server`
   - Check known_hosts file

2. **Platform Detection Issues**
   - Manually test commands on target system
   - Check platform detection: `uname -s`
   - Review platform-specific parsers

3. **UI Rendering Problems**
   - Ensure terminal supports UTF-8
   - Check terminal size
   - Try different terminal emulators

### Debug Mode
Run with environment variable:
```bash
RSM_DEBUG=1 rsm --config config.toml
```

## Performance Considerations

### Optimization Tips

1. **Batch Commands**
   - Use `execute_batch()` for multiple commands
   - Combine related metrics collection

2. **Caching**
   - Adjust cache durations based on metric volatility
   - Use platform caching for static info

3. **Connection Pooling**
   - Limit concurrent connections per server
   - Reuse connections when possible

4. **UI Updates**
   - Throttle update frequency for slow systems
   - Use partial updates when possible

## Release Process

1. **Update version**
   - Edit `rsm/__init__.py`
   - Update `pyproject.toml`

2. **Update documentation**
   - Update CHANGELOG.md
   - Review README.md

3. **Run full test suite**
   ```bash
   pytest
   black --check rsm/
   ruff check rsm/
   mypy rsm/
   ```

4. **Create release**
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run linting and tests
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

### Commit Message Convention

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build/tool changes

Example: `feat: add MySQL collector for database monitoring`

## Resources

- [Textual Documentation](https://textual.textualize.io/)
- [asyncssh Documentation](https://asyncssh.readthedocs.io/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [TOML Specification](https://toml.io/)