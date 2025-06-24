"""Pytest configuration and fixtures."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from rsm.core.ssh_manager import SSHConnectionPool, SSHConfig
from rsm.utils.platform import PlatformManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ssh_pool():
    """Create a mock SSH connection pool."""
    pool = AsyncMock(spec=SSHConnectionPool)
    pool.execute = AsyncMock()
    pool.execute_batch = AsyncMock()
    pool.add_server = AsyncMock()
    pool.close = AsyncMock()
    pool.get_connection = AsyncMock()
    pool.get_server_status = MagicMock(return_value="connected")
    return pool


@pytest.fixture
def mock_platform_manager():
    """Create a mock platform manager."""
    manager = AsyncMock(spec=PlatformManager)
    manager.detect_platform = AsyncMock()
    manager.get_commands = MagicMock()
    manager.get_server_commands = AsyncMock()
    return manager


@pytest.fixture
def ssh_config():
    """Create a test SSH configuration."""
    return SSHConfig(
        hostname="test.example.com",
        username="testuser",
        port=22
    )


@pytest.fixture
def sample_server_configs():
    """Create sample server configurations for testing."""
    return {
        "linux-server": SSHConfig("linux.example.com", "user"),
        "bsd-server": SSHConfig("bsd.example.com", "user"),
        "macos-server": SSHConfig("macos.example.com", "user"),
    }


# Sample command outputs for testing parsers
@pytest.fixture
def linux_cpu_output():
    """Linux /proc/stat output."""
    return "cpu  1000 200 800 7000 100 50 25 0 0 0"


@pytest.fixture
def linux_memory_output():
    """Linux /proc/meminfo output."""
    return """MemTotal:        8000000 kB
MemFree:         2000000 kB
MemAvailable:    3000000 kB
Buffers:          500000 kB
Cached:          1000000 kB
SwapTotal:       2000000 kB
SwapFree:        1500000 kB"""


@pytest.fixture
def disk_usage_output():
    """df -h output."""
    return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   10G   10G  50% /
/dev/sda2       100G   25G   75G  25% /home
tmpfs           4.0G     0  4.0G   0% /tmp"""


@pytest.fixture
def uptime_output():
    """uptime command output."""
    return "12:34:56 up 1 day, 2:34, 1 user, load average: 0.50, 0.75, 1.00"


@pytest.fixture
def bsd_cpu_output():
    """BSD top output."""
    return """
last pid: 12345;  load averages:  0.50,  0.75,  1.00
CPU: 25.0% user,  0.0% nice, 10.0% system,  5.0% interrupt, 60.0% idle
Mem: 1024M Active, 512M Inact, 256M Wired, 128M Cache, 64M Buf, 32M Free
"""


@pytest.fixture
def macos_cpu_output():
    """macOS top output."""
    return """
Processes: 234 total, 2 running, 232 sleeping, 1234 threads
CPU usage: 15.5% user, 5.2% sys, 79.3% idle
PhysMem: 8192M used (1234M wired), 2048M unused.
"""


@pytest.fixture
def macos_memory_output():
    """macOS vm_stat output."""
    return """Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                     512000.
Pages active:                  1024000.
Pages inactive:                 768000.
Pages speculative:              256000.
Pages throttled:                     0.
Pages wired down:               512000.
Pages purgeable:                128000.
Pages compressed:               384000."""