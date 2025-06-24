# Testing Guide - Remote Server Monitor

This document describes the testing strategy and how to run tests for the RSM project.

## Test Overview

The RSM project has a comprehensive test suite with **86 tests** providing excellent coverage of core components:

- **78 Unit Tests** - Testing individual components in isolation
- **8 Integration Tests** - Testing end-to-end workflows
- **94%+ Coverage** on critical components (SSH manager, platform abstraction, collectors)

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_ssh_manager.py  # SSH connection testing
│   ├── test_platform.py     # Platform abstraction testing
│   └── test_collectors.py   # Collector testing
└── integration/             # Integration tests
    ├── __init__.py
    └── test_full_system.py  # End-to-end system testing
```

## Running Tests

### Quick Test Run
```bash
# Run all tests
python -m pytest tests/

# Run only unit tests (faster)
python -m pytest tests/unit/

# Run with verbose output
python -m pytest tests/ -v
```

### Using Test Runner Script
```bash
# Full test suite with coverage
python run_tests.py

# Quick unit tests only
python run_tests.py quick

# Run linting and type checking
python run_tests.py lint

# Run everything (tests + linting)
python run_tests.py all
```

### Coverage Reports
```bash
# Generate coverage report
python -m pytest tests/ --cov=rsm --cov-report=term-missing

# Generate HTML coverage report
python -m pytest tests/ --cov=rsm --cov-report=html:htmlcov
# Then open htmlcov/index.html in your browser
```

## Test Categories

### Unit Tests

#### SSH Manager Tests (`test_ssh_manager.py`)
- **SSH Configuration**: Parameter validation and conversion to asyncssh options
- **Connection Pool**: Connection management, retry logic, and cleanup
- **Command Execution**: Single commands, batch commands, and error handling
- **Async Context Management**: Proper resource cleanup and connection status

#### Platform Abstraction Tests (`test_platform.py`)
- **Platform Detection**: Parsing uname output for Linux/BSD/macOS identification
- **Command Generation**: Platform-specific commands for metrics collection
- **Caching**: Platform detection and command object caching
- **Error Handling**: Unknown platforms and SSH failures

#### Collector Tests (`test_collectors.py`)
- **Base Collector**: Caching, async collection loops, and registry management
- **System Metrics**: CPU/memory/disk parsing for all supported platforms
- **Error Recovery**: Handling SSH failures and malformed command outputs
- **Metric Data**: Timestamp management and staleness detection

### Integration Tests

#### Full System Tests (`test_full_system.py`)
- **End-to-End Collection**: Complete metric collection workflow
- **Multi-Server Monitoring**: Concurrent monitoring of multiple servers
- **Platform Detection**: Automatic platform detection and command selection
- **Error Handling**: SSH failures and graceful degradation
- **Caching**: Metric caching and refresh behavior
- **Concurrent Operations**: Performance under concurrent load

## Test Dependencies

The test suite uses the following dependencies (installed via `pip install -e ".[dev]"`):

- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **unittest.mock** - Mocking for SSH operations
- **asyncio** - Async/await testing

## Writing Tests

### Test Conventions

1. **File Naming**: Test files should start with `test_` and match the module being tested
2. **Class Organization**: Group related tests in classes (e.g., `TestSSHConfig`, `TestSSHConnectionPool`)
3. **Descriptive Names**: Test method names should clearly describe what is being tested
4. **Async Support**: Use `@pytest.mark.asyncio` for async test methods
5. **Mocking**: Mock external dependencies (SSH connections, file system operations)

### Example Test Structure

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestMyComponent:
    """Test MyComponent class."""
    
    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return MyComponent()
    
    def test_sync_method(self, component):
        """Test synchronous method."""
        result = component.sync_method("input")
        assert result == "expected"
    
    @pytest.mark.asyncio
    async def test_async_method(self, component):
        """Test asynchronous method."""
        result = await component.async_method("input")
        assert result == "expected"
```

### Mocking SSH Operations

```python
@pytest.fixture
def mock_ssh_pool():
    """Create mock SSH pool for testing."""
    pool = AsyncMock(spec=SSHConnectionPool)
    pool.execute = AsyncMock(return_value="command output")
    pool.execute_batch = AsyncMock(return_value=["output1", "output2"])
    return pool
```

## Coverage Goals

We aim for the following coverage targets:

- **Core Components**: 90%+ coverage (SSH manager, collectors, platform abstraction)
- **UI Components**: 70%+ coverage (harder to test due to terminal interface)
- **Utilities**: 85%+ coverage
- **Overall Project**: 75%+ coverage

## Continuous Integration

Tests run automatically on:
- Every commit (pre-commit hooks)
- Pull requests 
- Main branch updates

The CI pipeline includes:
1. Unit and integration tests
2. Coverage reporting
3. Code linting (ruff)
4. Type checking (mypy)
5. Code formatting (black)

## Debugging Tests

### Common Issues

1. **Async Test Failures**: Ensure `@pytest.mark.asyncio` is used for async tests
2. **Mock Failures**: Verify mock setup matches actual usage patterns
3. **Platform-Specific Failures**: Use platform-specific test data

### Running Individual Tests

```bash
# Run specific test file
python -m pytest tests/unit/test_ssh_manager.py

# Run specific test class
python -m pytest tests/unit/test_ssh_manager.py::TestSSHConfig

# Run specific test method
python -m pytest tests/unit/test_ssh_manager.py::TestSSHConfig::test_ssh_config_creation

# Run with debugging output
python -m pytest tests/unit/test_ssh_manager.py -v -s
```

## Performance Testing

While not included in the current test suite, consider these areas for performance testing:

- SSH connection pooling efficiency
- Concurrent metric collection scaling
- Memory usage under load
- UI responsiveness with many servers

## Security Testing

Security considerations in testing:

- No real SSH credentials in test code
- Mock all external connections
- Test SSH key validation logic
- Verify configuration sanitization