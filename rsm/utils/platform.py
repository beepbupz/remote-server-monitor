"""Platform abstraction layer for cross-OS command compatibility."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Type
import logging


logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""
    
    LINUX = "linux"
    FREEBSD = "freebsd"
    OPENBSD = "openbsd"
    MACOS = "darwin"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_uname(cls, uname_output: str) -> "Platform":
        """Detect platform from uname output."""
        uname_lower = uname_output.lower()
        
        if "linux" in uname_lower:
            return cls.LINUX
        elif "freebsd" in uname_lower:
            return cls.FREEBSD
        elif "openbsd" in uname_lower:
            return cls.OPENBSD
        elif "darwin" in uname_lower:
            return cls.MACOS
        else:
            logger.warning(f"Unknown platform from uname: {uname_output}")
            return cls.UNKNOWN


class PlatformCommands(ABC):
    """Abstract base class for platform-specific commands."""
    
    @abstractmethod
    def cpu_info_cmd(self) -> str:
        """Command to get CPU information."""
        pass
    
    @abstractmethod
    def cpu_usage_cmd(self) -> str:
        """Command to get CPU usage."""
        pass
    
    @abstractmethod
    def memory_info_cmd(self) -> str:
        """Command to get memory information."""
        pass
    
    @abstractmethod
    def disk_usage_cmd(self) -> str:
        """Command to get disk usage."""
        pass
    
    @abstractmethod
    def network_info_cmd(self) -> str:
        """Command to get network interface information."""
        pass
    
    @abstractmethod
    def process_list_cmd(self) -> str:
        """Command to get process list."""
        pass
    
    @abstractmethod
    def uptime_cmd(self) -> str:
        """Command to get system uptime and load."""
        pass
    
    def service_status_cmd(self, service_name: str) -> str:
        """Command to check service status."""
        return f"pgrep -f {service_name}"


class LinuxCommands(PlatformCommands):
    """Linux-specific commands."""
    
    def cpu_info_cmd(self) -> str:
        return "lscpu 2>/dev/null || cat /proc/cpuinfo"
    
    def cpu_usage_cmd(self) -> str:
        return "cat /proc/stat"
    
    def memory_info_cmd(self) -> str:
        return "cat /proc/meminfo"
    
    def disk_usage_cmd(self) -> str:
        return "df -h"
    
    def network_info_cmd(self) -> str:
        return "cat /proc/net/dev"
    
    def process_list_cmd(self) -> str:
        return "ps aux --no-headers"
    
    def uptime_cmd(self) -> str:
        return "uptime"
    
    def service_status_cmd(self, service_name: str) -> str:
        """Try systemctl first, fall back to pgrep."""
        return (
            f"systemctl is-active {service_name} 2>/dev/null || "
            f"pgrep -f {service_name} >/dev/null && echo active || echo inactive"
        )


class BSDCommands(PlatformCommands):
    """BSD-specific commands (FreeBSD, OpenBSD)."""
    
    def cpu_info_cmd(self) -> str:
        return "sysctl -n hw.model hw.ncpu"
    
    def cpu_usage_cmd(self) -> str:
        return "top -b -n 1"
    
    def memory_info_cmd(self) -> str:
        return "sysctl -n hw.physmem hw.usermem vm.stats.vm.v_free_count"
    
    def disk_usage_cmd(self) -> str:
        return "df -h"
    
    def network_info_cmd(self) -> str:
        return "netstat -ibn"
    
    def process_list_cmd(self) -> str:
        return "ps aux"
    
    def uptime_cmd(self) -> str:
        return "uptime"


class MacOSCommands(PlatformCommands):
    """macOS-specific commands."""
    
    def cpu_info_cmd(self) -> str:
        return "sysctl -n machdep.cpu.brand_string machdep.cpu.core_count"
    
    def cpu_usage_cmd(self) -> str:
        return "top -l 1 -n 0"
    
    def memory_info_cmd(self) -> str:
        return "vm_stat"
    
    def disk_usage_cmd(self) -> str:
        return "df -h"
    
    def network_info_cmd(self) -> str:
        return "netstat -ibn"
    
    def process_list_cmd(self) -> str:
        return "ps aux"
    
    def uptime_cmd(self) -> str:
        return "uptime"


class PlatformManager:
    """Manages platform detection and command selection."""
    
    _platform_commands: Dict[Platform, Type[PlatformCommands]] = {
        Platform.LINUX: LinuxCommands,
        Platform.FREEBSD: BSDCommands,
        Platform.OPENBSD: BSDCommands,
        Platform.MACOS: MacOSCommands,
    }
    
    def __init__(self):
        self._platform_cache: Dict[str, Platform] = {}
        self._commands_cache: Dict[str, PlatformCommands] = {}
    
    async def detect_platform(self, ssh_pool, server: str) -> Platform:
        """Detect platform for a server."""
        if server in self._platform_cache:
            return self._platform_cache[server]
        
        try:
            uname_output = await ssh_pool.execute(server, "uname -s", timeout=5.0)
            platform = Platform.from_uname(uname_output.strip())
            self._platform_cache[server] = platform
            return platform
        except Exception as e:
            logger.error(f"Failed to detect platform for {server}: {e}")
            return Platform.UNKNOWN
    
    def get_commands(self, platform: Platform) -> PlatformCommands:
        """Get platform-specific commands."""
        if platform not in self._commands_cache:
            commands_class = self._platform_commands.get(platform, LinuxCommands)
            self._commands_cache[platform] = commands_class()
        
        return self._commands_cache[platform]
    
    async def get_server_commands(self, ssh_pool, server: str) -> PlatformCommands:
        """Get commands for a specific server."""
        platform = await self.detect_platform(ssh_pool, server)
        return self.get_commands(platform)