"""Unit tests for platform abstraction layer."""

import pytest
from unittest.mock import AsyncMock, patch

from rsm.utils.platform import (
    Platform, PlatformCommands, LinuxCommands, BSDCommands, 
    MacOSCommands, PlatformManager
)


class TestPlatform:
    """Test Platform enum."""
    
    def test_platform_enum_values(self):
        """Test platform enum values."""
        assert Platform.LINUX.value == "linux"
        assert Platform.FREEBSD.value == "freebsd"
        assert Platform.OPENBSD.value == "openbsd"
        assert Platform.MACOS.value == "darwin"
        assert Platform.UNKNOWN.value == "unknown"
    
    def test_from_uname_linux(self):
        """Test platform detection from Linux uname."""
        uname_outputs = [
            "Linux hostname 5.4.0-74-generic #83-Ubuntu SMP Sat May 8 02:35:39 UTC 2021 x86_64 x86_64 x86_64 GNU/Linux",
            "linux",
            "LINUX",
            "Linux"
        ]
        
        for output in uname_outputs:
            assert Platform.from_uname(output) == Platform.LINUX
    
    def test_from_uname_freebsd(self):
        """Test platform detection from FreeBSD uname."""
        uname_outputs = [
            "FreeBSD hostname 13.0-RELEASE FreeBSD 13.0-RELEASE",
            "freebsd",
            "FREEBSD",
            "FreeBSD"
        ]
        
        for output in uname_outputs:
            assert Platform.from_uname(output) == Platform.FREEBSD
    
    def test_from_uname_openbsd(self):
        """Test platform detection from OpenBSD uname."""
        uname_outputs = [
            "OpenBSD hostname 6.9 GENERIC.MP#3 amd64",
            "openbsd",
            "OPENBSD",
            "OpenBSD"
        ]
        
        for output in uname_outputs:
            assert Platform.from_uname(output) == Platform.OPENBSD
    
    def test_from_uname_macos(self):
        """Test platform detection from macOS uname."""
        uname_outputs = [
            "Darwin hostname 21.6.0 Darwin Kernel Version 21.6.0",
            "darwin",
            "DARWIN",
            "Darwin"
        ]
        
        for output in uname_outputs:
            assert Platform.from_uname(output) == Platform.MACOS
    
    def test_from_uname_unknown(self):
        """Test unknown platform detection."""
        uname_outputs = [
            "Windows",
            "SunOS",
            "AIX",
            "UnknownOS",
            "",
            "Some random text"
        ]
        
        for output in uname_outputs:
            assert Platform.from_uname(output) == Platform.UNKNOWN


class TestLinuxCommands:
    """Test Linux-specific commands."""
    
    @pytest.fixture
    def commands(self):
        """Create Linux commands instance."""
        return LinuxCommands()
    
    def test_linux_commands(self, commands):
        """Test Linux command generation."""
        assert "lscpu" in commands.cpu_info_cmd() or "/proc/cpuinfo" in commands.cpu_info_cmd()
        assert commands.cpu_usage_cmd() == "cat /proc/stat"
        assert commands.memory_info_cmd() == "cat /proc/meminfo"
        assert commands.disk_usage_cmd() == "df -h"
        assert commands.network_info_cmd() == "cat /proc/net/dev"
        assert "ps aux" in commands.process_list_cmd()
        assert commands.uptime_cmd() == "uptime"
    
    def test_linux_service_status(self, commands):
        """Test Linux service status command."""
        cmd = commands.service_status_cmd("nginx")
        assert "systemctl is-active nginx" in cmd
        assert "pgrep -f nginx" in cmd


class TestBSDCommands:
    """Test BSD-specific commands."""
    
    @pytest.fixture
    def commands(self):
        """Create BSD commands instance."""
        return BSDCommands()
    
    def test_bsd_commands(self, commands):
        """Test BSD command generation."""
        assert "sysctl" in commands.cpu_info_cmd()
        assert "hw.model" in commands.cpu_info_cmd()
        assert "top" in commands.cpu_usage_cmd()
        assert "sysctl" in commands.memory_info_cmd()
        assert "hw.physmem" in commands.memory_info_cmd()
        assert commands.disk_usage_cmd() == "df -h"
        assert "netstat -ibn" in commands.network_info_cmd()
        assert commands.process_list_cmd() == "ps aux"
        assert commands.uptime_cmd() == "uptime"


class TestMacOSCommands:
    """Test macOS-specific commands."""
    
    @pytest.fixture
    def commands(self):
        """Create macOS commands instance."""
        return MacOSCommands()
    
    def test_macos_commands(self, commands):
        """Test macOS command generation."""
        assert "sysctl" in commands.cpu_info_cmd()
        assert "machdep.cpu" in commands.cpu_info_cmd()
        assert "top -l 1 -n 0" in commands.cpu_usage_cmd()
        assert commands.memory_info_cmd() == "vm_stat"
        assert commands.disk_usage_cmd() == "df -h"
        assert "netstat -ibn" in commands.network_info_cmd()
        assert commands.process_list_cmd() == "ps aux"
        assert commands.uptime_cmd() == "uptime"


class TestPlatformManager:
    """Test platform manager."""
    
    @pytest.fixture
    def manager(self):
        """Create platform manager."""
        return PlatformManager()
    
    @pytest.fixture
    def mock_ssh_pool(self):
        """Create mock SSH pool."""
        pool = AsyncMock()
        pool.execute = AsyncMock()
        return pool
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager._platform_cache) == 0
        assert len(manager._commands_cache) == 0
    
    @pytest.mark.asyncio
    async def test_detect_platform_linux(self, manager, mock_ssh_pool):
        """Test Linux platform detection."""
        mock_ssh_pool.execute.return_value = "Linux"
        
        platform = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform == Platform.LINUX
        assert manager._platform_cache["test-server"] == Platform.LINUX
        mock_ssh_pool.execute.assert_called_once_with("test-server", "uname -s", timeout=5.0)
    
    @pytest.mark.asyncio
    async def test_detect_platform_freebsd(self, manager, mock_ssh_pool):
        """Test FreeBSD platform detection."""
        mock_ssh_pool.execute.return_value = "FreeBSD"
        
        platform = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform == Platform.FREEBSD
    
    @pytest.mark.asyncio
    async def test_detect_platform_macos(self, manager, mock_ssh_pool):
        """Test macOS platform detection."""
        mock_ssh_pool.execute.return_value = "Darwin"
        
        platform = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform == Platform.MACOS
    
    @pytest.mark.asyncio
    async def test_detect_platform_unknown(self, manager, mock_ssh_pool):
        """Test unknown platform detection."""
        mock_ssh_pool.execute.return_value = "UnknownOS"
        
        platform = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform == Platform.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_detect_platform_error(self, manager, mock_ssh_pool):
        """Test platform detection error handling."""
        mock_ssh_pool.execute.side_effect = Exception("SSH Error")
        
        platform = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform == Platform.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_detect_platform_caching(self, manager, mock_ssh_pool):
        """Test platform detection caching."""
        mock_ssh_pool.execute.return_value = "Linux"
        
        # First call
        platform1 = await manager.detect_platform(mock_ssh_pool, "test-server")
        # Second call should use cache
        platform2 = await manager.detect_platform(mock_ssh_pool, "test-server")
        
        assert platform1 == platform2 == Platform.LINUX
        # SSH should only be called once due to caching
        mock_ssh_pool.execute.assert_called_once()
    
    def test_get_commands_linux(self, manager):
        """Test getting Linux commands."""
        commands = manager.get_commands(Platform.LINUX)
        
        assert isinstance(commands, LinuxCommands)
        assert commands.cpu_usage_cmd() == "cat /proc/stat"
    
    def test_get_commands_freebsd(self, manager):
        """Test getting FreeBSD commands."""
        commands = manager.get_commands(Platform.FREEBSD)
        
        assert isinstance(commands, BSDCommands)
        assert "top" in commands.cpu_usage_cmd()
    
    def test_get_commands_openbsd(self, manager):
        """Test getting OpenBSD commands."""
        commands = manager.get_commands(Platform.OPENBSD)
        
        assert isinstance(commands, BSDCommands)
    
    def test_get_commands_macos(self, manager):
        """Test getting macOS commands."""
        commands = manager.get_commands(Platform.MACOS)
        
        assert isinstance(commands, MacOSCommands)
        assert commands.memory_info_cmd() == "vm_stat"
    
    def test_get_commands_unknown(self, manager):
        """Test getting commands for unknown platform."""
        commands = manager.get_commands(Platform.UNKNOWN)
        
        # Should default to Linux commands
        assert isinstance(commands, LinuxCommands)
    
    def test_get_commands_caching(self, manager):
        """Test command object caching."""
        commands1 = manager.get_commands(Platform.LINUX)
        commands2 = manager.get_commands(Platform.LINUX)
        
        # Should return the same cached instance
        assert commands1 is commands2
    
    @pytest.mark.asyncio
    async def test_get_server_commands(self, manager, mock_ssh_pool):
        """Test getting commands for a specific server."""
        mock_ssh_pool.execute.return_value = "Linux"
        
        commands = await manager.get_server_commands(mock_ssh_pool, "test-server")
        
        assert isinstance(commands, LinuxCommands)
        # Should have cached the platform
        assert manager._platform_cache["test-server"] == Platform.LINUX
    
    @pytest.mark.asyncio
    async def test_get_server_commands_cached(self, manager, mock_ssh_pool):
        """Test getting server commands with cached platform."""
        # Pre-populate cache
        manager._platform_cache["test-server"] = Platform.MACOS
        
        commands = await manager.get_server_commands(mock_ssh_pool, "test-server")
        
        assert isinstance(commands, MacOSCommands)
        # SSH should not be called due to caching
        mock_ssh_pool.execute.assert_not_called()