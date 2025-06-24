# Changelog

All notable changes to the Remote Server Monitor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2025-06-24

### Added - Comprehensive Testing Infrastructure

#### Testing Framework
- **Complete Unit Test Suite** (78 tests)
  - SSH Manager testing with mock connections and retry logic
  - Platform abstraction testing across Linux/BSD/macOS
  - Collector base class testing with caching and async operations
  - System metrics collector testing with platform-specific parsing
  - Configuration and utility testing
  
- **Integration Test Suite** (8 tests)
  - End-to-end metric collection workflows
  - Multi-server concurrent monitoring
  - Error handling and recovery scenarios
  - Cache functionality and performance testing
  - Platform detection and command execution

#### Test Infrastructure
- **pytest-asyncio** support for async testing
- **Comprehensive mocking** for SSH operations and external dependencies
- **Coverage reporting** with pytest-cov (94%+ coverage on core components)
- **Test organization** with unit/integration separation
- **Test runner script** (`run_tests.py`) with coverage and linting options

#### Quality Improvements
- **Bug fixes** discovered during testing:
  - Improved disk usage parsing logic to correctly filter filesystem types
  - Enhanced error handling in system metrics collection
  - Fixed batch command execution string handling
- **Version consistency** fix between `__init__.py` and `pyproject.toml`

### Technical Details
- **Test Coverage**: 86 tests total with excellent coverage
  - SSH Manager: 94% coverage
  - Platform abstraction: 93% coverage
  - Collector base: 97% coverage
  - System collector: 68% coverage (remaining are error paths)
- **Files Added**: Complete test suite structure with fixtures and utilities
- **Testing Strategy**: Isolated unit tests + comprehensive integration tests

## [0.2.0] - 2025-06-24

### Added - Service Monitoring (Phase 4)

#### Service Collectors
- **WebServer Collector** (`rsm/collectors/webserver.py`)
  - Apache and Nginx monitoring with status, ports, and configuration validation
  - Performance metrics collection (mod_status, stub_status)
  - Process count and worker monitoring
  - Connection and request statistics

- **Database Collector** (`rsm/collectors/database.py`)
  - MySQL, PostgreSQL, and Redis monitoring
  - Accessibility checks and connection statistics
  - Version information and performance metrics
  - Database count and uptime tracking

- **Process Collector** (`rsm/collectors/process.py`)
  - Node.js, Python, Java, and Docker process monitoring
  - CPU and memory usage tracking per process type
  - PM2 process manager integration
  - Container listing and system information

#### UI Enhancements
- **Service Status Widgets** (`rsm/ui/widgets/service_widgets.py`)
  - WebServerWidget for Apache/Nginx status display
  - DatabaseWidget for database accessibility and metrics
  - ProcessWidget with tabular process resource usage
  - Color-coded health indicators (green/yellow/red)

- **Enhanced Dashboard Layout**
  - Extended server dashboard with service monitoring sections
  - Improved scrollable container for better navigation
  - New CSS styling for service widgets
  - Responsive design for different terminal sizes

#### Architecture Improvements
- Modular collector design following established patterns
- Cross-platform command compatibility (Linux/BSD/macOS)
- Graceful degradation for unavailable services
- Concurrent command execution for improved performance
- Type-safe implementation with comprehensive annotations

### Changed
- Updated collector registry to include new service collectors
- Enhanced main application with automatic service collector registration
- Improved error handling and logging throughout service monitoring

### Technical Details
- **Files Added**: 4 new files (webserver.py, database.py, process.py, service_widgets.py)
- **Files Modified**: 3 existing files enhanced with new functionality
- **Total LOC Added**: ~1,500 lines of production-ready code
- **Services Supported**: Apache, Nginx, MySQL, PostgreSQL, Redis, Node.js, Python, Java, Docker

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