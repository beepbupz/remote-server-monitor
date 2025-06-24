# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Remote Server Monitor (RSM) - A terminal-based SSH monitoring tool for multiple remote servers without requiring agent installation.

## Technology Stack

- **Language**: Python 3.9+
- **UI Framework**: Textual 0.40+
- **SSH Library**: asyncssh 2.14+
- **Configuration**: TOML format
- **Testing**: pytest + pytest-asyncio
- **Async**: asyncio

## Architecture

The project follows an agent-less architecture using SSH to execute commands remotely:

- **Core Engine**: Manages SSH connections and command execution
- **Data Collection**: Gathers metrics via SSH commands
- **UI Layer**: Terminal interface built with Textual
- **Plugin System**: Modular architecture for extending functionality
- **Export System**: Supports JSON, Prometheus, and CSV formats

## Key Design Decisions

1. **Agent-less**: No installation required on monitored servers
2. **Cross-platform**: Supports Linux, FreeBSD, OpenBSD, and macOS
3. **Async-first**: Uses asyncio for concurrent server monitoring
4. **Modular**: Plugin architecture for custom monitoring needs

## Development Commands

### Installation
- Install dependencies: `pip install -e .`
- Install with dev dependencies: `pip install -e ".[dev]"`

### Running
- Run the monitor: `rsm --config config.toml`
- Run from module: `python -m rsm --config config.toml`
- Show help: `rsm --help`
- Show version: `rsm --version`

### Development
- Run tests: `pytest`
- Run tests with coverage: `pytest --cov=rsm`
- Format code: `black rsm/`
- Lint code: `ruff check rsm/`
- Type check: `mypy rsm/`

### Configuration
- Copy example config: `cp config.toml.example config.toml`
- Edit servers in config.toml before running

## Project Status

Initial implementation completed with:
- Core SSH connection manager with pooling and reconnection
- Platform abstraction layer for Linux/BSD/macOS
- System metrics collector (CPU, memory, disk, load)
- Basic Textual UI with tabbed multi-server view
- TOML-based configuration system

Next phases (per PDR):
- Service monitoring (web servers, databases)
- Log tailing with filters
- Plugin architecture
- Data export (Prometheus, JSON)

## License

Source-available license (Commons Clause + Apache 2.0) - allows modifications but restricts commercial use.