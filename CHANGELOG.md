# Changelog

All notable changes to the Remote Server Monitor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-24

### Added - Initial Implementation

#### Project Foundation
- Created complete project structure with Python packaging
- Set up `pyproject.toml` with all dependencies and project metadata
- Added development dependencies for testing, linting, and type checking
- Created entry point script with Click CLI framework
- Added `requirements.txt` for easy dependency installation

#### Core Components
- **SSH Connection Manager** (`rsm/core/ssh_manager.py`)
  - Implemented async SSH connection pooling using asyncssh
  - Added automatic reconnection with exponential backoff
  - Support for SSH key and password authentication
  - Batch command execution for performance
  - Connection status tracking
  - Context manager support for proper cleanup

- **Platform Abstraction Layer** (`rsm/utils/platform.py`)
  - Cross-platform command mappings for Linux, BSD, and macOS
  - Automatic platform detection via uname
  - Platform-specific commands for CPU, memory, disk, network, and processes
  - Command caching to reduce SSH overhead

- **Configuration Management** (`rsm/core/config.py`)
  - TOML-based configuration with tomli/tomli_w
  - Dataclass-based config structure for type safety
  - Configuration validation with detailed error messages
  - Support for multiple servers with individual settings
  - Collector-specific interval configuration
  - Export options for Prometheus and JSON

#### Metric Collection
- **Base Collector Architecture** (`rsm/collectors/base.py`)
  - Abstract base class for all metric collectors
  - Built-in caching mechanism with configurable TTL
  - Async metric collection with concurrent server support
  - Automatic collection loops with customizable intervals
  - Collector registry for managing multiple collectors
  - Error handling with metric-level error reporting

- **System Metrics Collector** (`rsm/collectors/system.py`)
  - CPU usage parsing for all supported platforms
  - Memory statistics including buffers/cache on Linux
  - Disk usage with mount point information
  - System load averages (1, 5, 15 minute)
  - Platform-specific parsing logic for each OS

#### Terminal UI
- **Main Application** (`rsm/ui/app.py`)
  - Textual-based terminal interface
  - Tabbed interface for multiple servers
  - Real-time metric updates
  - Keyboard shortcuts (q=quit, r=refresh)
  - Automatic metric refresh based on poll interval
  - Error notifications in the UI

- **Metric Widgets**
  - CPU widget with progress bar and color coding
  - Memory widget showing usage percentage and GB values
  - Disk widget with table of mount points
  - Load average widget with simple visualization
  - Color coding based on thresholds (green/yellow/red)

#### Documentation
- Comprehensive README with installation and usage instructions
- Example configuration file with detailed comments
- CLAUDE.md for AI assistant context
- This CHANGELOG to track project evolution

### Technical Decisions
- Chose `asyncssh` over `paramiko` for better async support
- Used `asyncio` throughout for concurrent operations
- Selected Textual for modern TUI capabilities
- Implemented caching at multiple levels for performance
- Used dataclasses for configuration management
- Followed modular architecture for extensibility

### Project Structure
```
rsm/
├── __init__.py
├── __main__.py          # Entry point
├── core/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   └── ssh_manager.py   # SSH connection pooling
├── collectors/
│   ├── __init__.py
│   ├── base.py          # Base collector classes
│   └── system.py        # System metrics collector
├── ui/
│   ├── __init__.py
│   ├── app.py           # Main Textual application
│   ├── widgets/         # Custom widgets (future)
│   └── screens/         # Screen definitions (future)
└── utils/
    ├── __init__.py
    └── platform.py      # Platform abstraction
```

## [Unreleased] - Future Development

### Planned Features (from PDR)
- Network metrics collector
- Service monitoring (Apache, Nginx, Node.js, databases)
- Log tailing with regex filtering
- Plugin architecture for extensibility
- Data export (Prometheus metrics, JSON, CSV)
- Historical data storage
- Alert notifications
- Performance optimizations
- Extended platform support